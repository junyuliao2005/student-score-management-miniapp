"""Permission-aware XLSX/PDF reports returned as Base64 for local/cloud clients."""
import base64
import io
from datetime import datetime

from sqlalchemy import and_, or_

from app.extensions import db
from app.models.course import Course
from app.models.exam_publish import ParentStudentBinding
from app.models.score import Score
from app.models.user import User
from app.services import exam_publish_service, teacher_scope_service
from app.utils.errors import BusinessError, ErrorCode


def export_scores_xlsx(current_user, filters):
    exam_batch = str((filters or {}).get('exam_batch') or '').strip()
    if not exam_batch:
        raise BusinessError(ErrorCode.INVALID_PARAMETER, '请先选择考试批次后导出成绩')
    query = _score_query().filter(Score.exam_batch == exam_batch)
    query = teacher_scope_service.apply_score_scope(query, current_user)
    query = _apply_filters(query, filters)
    rows = query.order_by(User.class_name, Score.student_id, Score.course_id).limit(10001).all()
    if len(rows) > 10000:
        raise BusinessError(ErrorCode.INVALID_PARAMETER, '单次导出不能超过 10000 条，请缩小班级或课程范围')
    try:
        from openpyxl import Workbook
    except ImportError as exc:
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, '缺少 openpyxl，无法导出成绩') from exc
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = '成绩导出'
    sheet.append(['学号', '姓名', '班级', '课程号', '课程名称', '分数', '考试日期', '考试批次', '学期'])
    for row in rows:
        sheet.append([
            row.student_id, row.student_name, row.class_name, row.course_id, row.course_name,
            float(row.score), row.exam_date.strftime('%Y-%m-%d') if row.exam_date else None,
            row.exam_batch, row.term,
        ])
    output = io.BytesIO()
    workbook.save(output)
    return _encoded_file(
        f'scores-{datetime.now().strftime("%Y%m%d-%H%M%S")}.xlsx',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        output.getvalue(),
        len(rows),
    )


def student_score_pdf(current_user, student_id, term=None, exam_batch=None):
    roles = (current_user or {}).get('roles') or []
    actor_id = (current_user or {}).get('user_id')
    staff_scope = False
    if 'student' in roles and 'teacher' not in roles and 'admin' not in roles:
        student_id = actor_id
        publication_required = True
    elif 'parent' in roles and 'teacher' not in roles and 'admin' not in roles:
        binding = ParentStudentBinding.query.filter_by(
            parent_user_id=actor_id, student_user_id=student_id, status=1,
        ).first()
        if not binding:
            raise BusinessError(ErrorCode.PERMISSION_DENIED, '家长未绑定该学生')
        publication_required = True
    elif 'teacher' in roles or 'admin' in roles:
        teacher_scope_service.ensure_access(current_user, student_id=student_id)
        publication_required = False
        staff_scope = True
    else:
        raise BusinessError(ErrorCode.PERMISSION_DENIED, '无权生成学生成绩报告')

    student = db.session.query(User.user_id, User.real_name, User.class_name).filter(
        User.user_id == student_id, User.status == 1,
    ).first()
    if not student:
        raise BusinessError(ErrorCode.STUDENT_NOT_FOUND, '学生不存在或已停用')
    query = _score_query().filter(Score.student_id == student_id)
    if staff_scope:
        query = teacher_scope_service.apply_score_scope(query, current_user)
    if term:
        query = query.filter(Course.term == term)
    if exam_batch:
        query = query.filter(Score.exam_batch == exam_batch)
    if publication_required:
        settings = exam_publish_service.get_published_settings_for_student(
            student_id, {'term': term, 'exam_batch': exam_batch},
        )
        visible_pairs = {
            (setting.term, setting.exam_batch)
            for setting in settings
            if setting.show_subject_scores
        }
        if not visible_pairs:
            raise BusinessError(ErrorCode.PERMISSION_DENIED, '暂无可生成报告的已发布成绩')
        query = query.filter(or_(*[
            and_(Course.term == visible_term, Score.exam_batch == visible_batch)
            for visible_term, visible_batch in visible_pairs
        ]))
    rows = query.order_by(Score.exam_date, Score.exam_batch, Score.course_id).all()
    if not rows:
        raise BusinessError(ErrorCode.STUDENT_NOT_FOUND, '当前筛选条件下没有可生成报告的成绩')
    report_rows = [
        {
            'course_id': row.course_id,
            'course_name': row.course_name or row.course_id,
            'score': float(row.score),
            'exam_date': row.exam_date.strftime('%Y-%m-%d') if row.exam_date else '',
            'exam_batch': row.exam_batch,
            'term': row.term,
        }
        for row in rows
    ]
    pdf_bytes = _build_pdf(student, report_rows)
    return _encoded_file(
        f'student-score-report-{student_id}.pdf', 'application/pdf', pdf_bytes, len(report_rows),
    )


def _score_query():
    return db.session.query(
        Score.student_id,
        User.real_name.label('student_name'),
        User.class_name,
        Score.course_id,
        Course.course_name,
        Score.score,
        Score.exam_date,
        Score.exam_batch,
        Course.term.label('term'),
    ).select_from(Score).join(User, Score.student_id == User.user_id) \
        .join(Course, Score.course_id == Course.course_id) \
        .filter(Score.status == 1, User.status == 1)


def _apply_filters(query, filters):
    if filters.get('term'):
        query = query.filter(Course.term == filters['term'])
    if filters.get('class_name'):
        query = query.filter(User.class_name == filters['class_name'])
    if filters.get('course_id'):
        query = query.filter(Score.course_id == filters['course_id'])
    if filters.get('student_id'):
        query = query.filter(Score.student_id == filters['student_id'])
    return query


def _build_pdf(student, rows):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as exc:
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, 'PDF 依赖未安装，请安装 reportlab') from exc
    output = io.BytesIO()
    pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
    document = SimpleDocTemplate(output, pagesize=A4, title='学生成绩报告')
    styles = getSampleStyleSheet()
    for style_name in ('Title', 'Normal'):
        styles[style_name].fontName = 'STSong-Light'
    values = [row['score'] for row in rows]
    story = [
        Paragraph('学生成绩报告', styles['Title']),
        Paragraph(
            f'学生：{student.real_name}（{student.user_id}）　班级：{student.class_name or "-"}',
            styles['Normal'],
        ),
        Paragraph(
            f'科目记录：{len(rows)}　平均分：{sum(values) / len(values):.2f}　最高分：{max(values):.2f}　最低分：{min(values):.2f}',
            styles['Normal'],
        ),
        Spacer(1, 12),
    ]
    table_data = [['学期', '考试批次', '课程', '分数', '考试日期']]
    table_data.extend([
        [row['term'], row['exam_batch'], row['course_name'], f"{row['score']:.2f}", row['exam_date']]
        for row in rows
    ])
    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'STSong-Light'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E8F3FF')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('ALIGN', (3, 1), (3, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    document.build(story)
    return output.getvalue()


def _encoded_file(filename, mime_type, content, row_count):
    return {
        'filename': filename,
        'mime_type': mime_type,
        'content_base64': base64.b64encode(content).decode('ascii'),
        'row_count': row_count,
    }
