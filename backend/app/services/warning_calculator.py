"""风险预警计算服务：低分预警、偏科预警"""
import logging
from app.extensions import db
from app.models.score import Score
from app.models.user import User
from app.models.course import Course
from app.services import config_loader, teacher_scope_service
from app.utils.validators import validate_pagination

logger = logging.getLogger(__name__)


def build_warnings(student_id, term, session=None, allowed_course_ids=None):
    """
    生成某学生某学期的预警列表。
    返回 list[dict]，每个元素包含 warning_type 等字段。
    """
    # 预警总开关
    if not config_loader.get_int('warning.enabled', 1):
        return []

    low_threshold = config_loader.get_int('warning.low_score.threshold', 60)
    bias_delta = config_loader.get_int('warning.subject_bias.delta', 20)

    records = Score.query.filter_by(student_id=student_id, status=1) \
        .join(Course, Score.course_id == Course.course_id) \
        .filter(Course.term == term)
    if allowed_course_ids is not None:
        records = records.filter(Score.course_id.in_(allowed_course_ids))
    records = records.all()

    if not records:
        return []

    warnings = []
    scores_list = []
    score_records = []

    for r in records:
        s = float(r.score)
        scores_list.append(s)
        score_records.append((s, r))
        # 低分预警
        if s < low_threshold:
            course_name = r.course.course_name if r.course else r.course_id
            warnings.append({
                'warning_type': 'low_score',
                'course_id': r.course_id,
                'course_name': course_name,
                'reason': f'{course_name} 成绩 {s:g} 低于预警线',
                'score': s,
            })

    # 偏科预警
    if len(scores_list) >= 2:
        max_s, max_record = max(score_records, key=lambda item: item[0])
        min_s, min_record = min(score_records, key=lambda item: item[0])
        bias = max_s - min_s
        if max_s - min_s >= bias_delta:
            max_subject = max_record.course.course_name if max_record.course else max_record.course_id
            min_subject = min_record.course.course_name if min_record.course else min_record.course_id
            warnings.append({
                'warning_type': 'subject_bias',
                'reason': f'最高 {max_subject}({max_s:g}) - 最低 {min_subject}({min_s:g}) = {bias:g}',
                'max_subject': max_subject,
                'min_subject': min_subject,
                'max_score': max_s,
                'min_score': min_s,
                'bias': bias,
            })

    # 排序：低分优先
    warnings.sort(key=lambda w: 0 if w['warning_type'] == 'low_score' else 1)
    return warnings


def get_warning_list(filters=None, page=1, page_size=20, current_user=None):
    """
    教师/管理员查询预警名单。
    实时计算，不持久化。按需扫描所有学生的成绩。
    """
    filters = filters or {}
    page, page_size = validate_pagination({'page': page, 'page_size': page_size})

    term = filters.get('term')
    class_name = filters.get('class_name')
    warning_type_filter = filters.get('warning_type')

    # 查询所有有成绩的学生
    query = db.session.query(Score.student_id).filter(Score.status == 1)
    allowed_course_ids = None
    if current_user is not None:
        query = teacher_scope_service.apply_score_scope(query, current_user)
        if teacher_scope_service.is_teacher(current_user) and not teacher_scope_service.is_admin(current_user):
            allowed_course_ids = teacher_scope_service.get_scope(current_user)['course_ids']
    if term:
        query = query.join(Course, Score.course_id == Course.course_id).filter(Course.term == term)
    if class_name:
        query = query.join(User, Score.student_id == User.user_id).filter(User.class_name == class_name)

    student_ids = list(set([row[0] for row in query.all()]))

    # 逐学生计算预警
    all_warnings = []
    for sid in student_ids:
        if not term:
            # 如果没指定学期，查询该学生所有学期
            terms = db.session.query(Course.term).join(Score, Score.course_id == Course.course_id) \
                .filter(Score.student_id == sid, Score.status == 1).distinct().all()
            for t in terms:
                warns = build_warnings(sid, t[0], allowed_course_ids=allowed_course_ids)
                for w in warns:
                    w['student_id'] = sid
                all_warnings.extend(warns)
        else:
            warns = build_warnings(sid, term, allowed_course_ids=allowed_course_ids)
            for w in warns:
                w['student_id'] = sid
            all_warnings.extend(warns)

    # 补充学生信息
    for w in all_warnings:
        student = User.query.filter_by(user_id=w['student_id']).first()
        w['student_name'] = student.real_name if student else None
        w['class_name'] = student.class_name if student else None

    # 按类型过滤
    if warning_type_filter:
        all_warnings = [w for w in all_warnings if w['warning_type'] == warning_type_filter]

    total = len(all_warnings)
    start = (page - 1) * page_size
    end = start + page_size
    paged = all_warnings[start:end]

    return {
        'list': paged,
        'page': page,
        'page_size': page_size,
        'total': total,
        'total_pages': (total + page_size - 1) // page_size,
    }


def refresh_warnings(term=None, class_name=None, operator_id=None, trace_id=None, current_user=None):
    """刷新预警（当前为按需计算，此接口返回成功状态即可）"""
    if current_user is not None and class_name:
        teacher_scope_service.ensure_access(current_user, class_name=class_name)
    return {
        'task_status': 'done',
        'message': '预警数据按需计算，查询时实时生成',
    }
