"""成绩管理服务：录入、修改、查询"""
import logging
from decimal import Decimal, InvalidOperation
from datetime import datetime
from sqlalchemy import and_, or_

from app.extensions import db
from app.models.score import Score
from app.models.user import User
from app.models.course import Course
from app.services import audit_service, teacher_scope_service
from app.services import config_loader, stats_service
from app.utils.errors import BusinessError, ErrorCode
from app.utils.validators import validate_pagination

logger = logging.getLogger(__name__)


def create_score(payload, operator_id, trace_id, current_user, commit=True):
    """
    新增成绩记录。
    校验：必填字段、分数范围、学生存在性、课程存在性、唯一性约束。
    """
    # 校验必填字段
    _validate_required_fields(payload, ['student_id', 'course_id', 'score', 'exam_date', 'exam_batch'])

    student_id = str(payload['student_id']).strip()
    course_id = str(payload['course_id']).strip()
    exam_batch = str(payload['exam_batch']).strip()
    exam_date = _parse_date(payload['exam_date'])
    score_value = _validate_score(payload['score'])

    # 校验学生存在且状态启用
    student = User.query.filter_by(user_id=student_id).first()
    if not student or student.status != 1:
        raise BusinessError(ErrorCode.STUDENT_NOT_FOUND, '学生不存在或状态异常',
                            data={'student_id': student_id})

    # 校验课程存在且启用
    course = Course.query.filter_by(course_id=course_id).first()
    if not course:
        raise BusinessError(ErrorCode.COURSE_NOT_FOUND, '课程不存在',
                            data={'course_id': course_id})
    if course.status != 1:
        raise BusinessError(ErrorCode.COURSE_NOT_FOUND, '课程已停用',
                            data={'course_id': course_id})

    teacher_scope_service.ensure_access(
        current_user, student_id=student_id, course_id=course_id,
    )

    # 唯一性检查：同一学生 + 同一课程 + 同一批次
    existing = Score.query.filter_by(
        student_id=student_id,
        course_id=course_id,
        exam_batch=exam_batch,
        status=1,
    ).first()
    if existing:
        raise BusinessError(ErrorCode.SCORE_DUPLICATE, '该学生该课程该批次成绩已存在',
                            data={'score_id': existing.score_id})

    # 写入
    try:
        record = Score(
            student_id=student_id,
            course_id=course_id,
            score=score_value,
            exam_date=exam_date,
            exam_batch=exam_batch,
            status=1,
            stat_version=0,
        )
        db.session.add(record)
        db.session.flush()

        # 审计日志
        audit_service.write(
            action='score.create',
            operator_id=operator_id,
            target_type='score',
            target_id=record.score_id,
            detail={
                'student_id': student_id,
                'course_id': course_id,
                'score': float(score_value),
                'exam_batch': exam_batch,
            },
            trace_id=trace_id,
        )

        # 触发统计刷新
        stats_service.refresh_student_derived(student_id, course.term)
        stats_service.refresh_rankings(term=course.term, class_name=student.class_name)

        if commit:
            db.session.commit()
        else:
            db.session.flush()

        return {
            'score_id': record.score_id,
            'student_id': student_id,
            'course_id': course_id,
            'score': float(score_value),
            'exam_date': exam_date.strftime('%Y-%m-%d'),
            'exam_batch': exam_batch,
            'task_status': 'done',
        }
    except BusinessError:
        if commit:
            db.session.rollback()
        raise
    except Exception as e:
        if commit:
            db.session.rollback()
        logger.error(f'成绩写入失败: {e}', exc_info=True)
        raise BusinessError(ErrorCode.DB_TRANSACTION_FAILED, '数据库事务失败')


def update_score(score_id, payload, operator_id, trace_id, current_user):
    """
    修改成绩记录。
    校验：记录存在、分数范围、唯一性冲突。
    """
    record = Score.query.filter_by(score_id=score_id).first()
    if not record:
        raise BusinessError(ErrorCode.STUDENT_NOT_FOUND, '成绩记录不存在',
                            data={'score_id': score_id})
    teacher_scope_service.ensure_access(
        current_user, student_id=record.student_id, course_id=record.course_id,
    )

    # 记录原始值用于审计
    before = {
        'score': float(record.score),
        'exam_date': record.exam_date.strftime('%Y-%m-%d'),
        'exam_batch': record.exam_batch,
    }

    # 更新分数
    if 'score' in payload and payload['score'] is not None:
        record.score = _validate_score(payload['score'])

    # 更新考试日期
    if 'exam_date' in payload and payload['exam_date'] is not None:
        record.exam_date = _parse_date(payload['exam_date'])

    # 更新考试批次（需要检查唯一性）
    if 'exam_batch' in payload and payload['exam_batch'] is not None:
        new_batch = str(payload['exam_batch']).strip()
        if new_batch != record.exam_batch:
            # 检查新组合是否冲突
            conflict = Score.query.filter(
                Score.score_id != score_id,
                Score.student_id == record.student_id,
                Score.course_id == record.course_id,
                Score.exam_batch == new_batch,
                Score.status == 1,
            ).first()
            if conflict:
                raise BusinessError(ErrorCode.SCORE_DUPLICATE, '修改后成绩批次重复')
            record.exam_batch = new_batch

    # 标记统计待刷新
    record.stat_version = 0

    try:
        db.session.flush()

        after = {
            'score': float(record.score),
            'exam_date': record.exam_date.strftime('%Y-%m-%d'),
            'exam_batch': record.exam_batch,
        }

        audit_service.write(
            action='score.update',
            operator_id=operator_id,
            target_type='score',
            target_id=score_id,
            detail={'before': before, 'after': after},
            trace_id=trace_id,
        )

        # 触发统计刷新
        course = Course.query.filter_by(course_id=record.course_id).first()
        student = User.query.filter_by(user_id=record.student_id).first()
        if course and student:
            stats_service.refresh_student_derived(record.student_id, course.term)
            stats_service.refresh_rankings(term=course.term, class_name=student.class_name)

        db.session.commit()

        return {
            'score_id': score_id,
            'task_status': 'done',
        }
    except BusinessError:
        db.session.rollback()
        raise
    except Exception as e:
        db.session.rollback()
        logger.error(f'成绩修改失败: {e}', exc_info=True)
        raise BusinessError(ErrorCode.DB_TRANSACTION_FAILED, '数据库事务失败')


def list_scores(filters=None, page=1, page_size=20, current_user=None):
    """
    教师/管理员分页查询成绩。
    支持筛选：student_id, student_name, course_id, course_name, class_name, term, exam_batch
    """
    page, page_size = validate_pagination({'page': page, 'page_size': page_size})
    filters = filters or {}

    query = db.session.query(
        Score.score_id,
        Score.student_id,
        User.real_name.label('student_name'),
        User.class_name,
        Score.course_id,
        Course.course_name,
        Score.score,
        Score.exam_date,
        Score.exam_batch,
        Score.total_score,
        Score.avg_score,
        Score.rank_no,
        Score.level_tag,
        Score.comment_text,
        Score.stat_version,
    ).select_from(Score).join(
        User, Score.student_id == User.user_id
    ).join(
        Course, Score.course_id == Course.course_id
    ).filter(Score.status == 1, User.status == 1)
    query = teacher_scope_service.apply_score_scope(query, current_user)

    # 筛选条件
    if filters.get('student_id'):
        query = query.filter(Score.student_id == filters['student_id'])
    if filters.get('student_name'):
        query = query.filter(User.real_name.like(f"%{filters['student_name']}%"))
    if filters.get('course_id'):
        query = query.filter(Score.course_id == filters['course_id'])
    if filters.get('course_name'):
        query = query.filter(Course.course_name.like(f"%{filters['course_name']}%"))
    if filters.get('class_name'):
        query = query.filter(User.class_name == filters['class_name'])
    if filters.get('term'):
        query = query.filter(Course.term == filters['term'])
    if filters.get('exam_batch'):
        query = query.filter(Score.exam_batch == filters['exam_batch'])

    total = query.count()
    total_pages = (total + page_size - 1) // page_size

    items = query.order_by(User.class_name, Score.student_id, Score.exam_batch, Course.course_id) \
        .offset((page - 1) * page_size) \
        .limit(page_size) \
        .all()

    result_list = []
    for s in items:
        result_list.append({
            'score_id': s.score_id,
            'student_id': s.student_id,
            'student_name': s.student_name,
            'class_name': s.class_name,
            'course_id': s.course_id,
            'course_name': s.course_name,
            'score': float(s.score),
            'exam_date': s.exam_date.strftime('%Y-%m-%d') if s.exam_date else None,
            'exam_batch': s.exam_batch,
            'total_score': float(s.total_score) if s.total_score is not None else None,
            'avg_score': float(s.avg_score) if s.avg_score is not None else None,
            'rank_no': s.rank_no,
            'level_tag': s.level_tag,
            'comment_text': s.comment_text,
            'stat_version': s.stat_version,
        })

    return {
        'list': result_list,
        'page': page,
        'page_size': page_size,
        'total': total,
        'total_pages': total_pages,
    }


def get_my_scores(student_id, filters=None):
    """
    学生查询自己的成绩。
    返回学生基本信息和成绩列表。
    """
    filters = filters or {}

    # 只查询学生页面需要的字段，避免 User.roles 的 joined eager load 带出角色/权限大联表。
    student = db.session.query(
        User.user_id,
        User.real_name,
        User.class_name,
    ).filter(
        User.user_id == student_id,
        User.status == 1,
    ).first()
    if not student:
        raise BusinessError(ErrorCode.STUDENT_NOT_FOUND, '学生不存在')

    from app.services import exam_publish_service
    published_settings = exam_publish_service.get_published_settings_for_student(student_id, filters)
    display_override = exam_publish_service.first_display_settings(published_settings)
    if not published_settings:
        return _my_scores_response(student, [], None, display_override, compatibility_mode=False)

    resolved_course_id = None
    if filters.get('course_id'):
        resolved_course_id = _resolve_course_id(filters['course_id'])

    # 学生端只查询当前登录学生自己的成绩，且只取页面需要字段，避免 Score.student/Course.teacher eager load。
    query = db.session.query(
        Score.score_id,
        Score.course_id,
        Course.course_name,
        Course.term,
        Score.score,
        Score.exam_date,
        Score.exam_batch,
        Score.total_score,
        Score.avg_score,
        Score.rank_no,
        Score.level_tag,
        Score.comment_text,
        Score.stat_version,
    ).join(
        Course, Score.course_id == Course.course_id
    ).filter(
        Score.student_id == student_id,
        Score.status == 1,
    )

    if filters.get('term'):
        query = query.filter(Course.term == filters['term'])
    if resolved_course_id:
        query = query.filter(Score.course_id == resolved_course_id)
    if filters.get('exam_batch'):
        query = query.filter(Score.exam_batch == filters['exam_batch'])
    publish_filters = [
        and_(Course.term == setting.term, Score.exam_batch == setting.exam_batch)
        for setting in published_settings
    ]
    query = query.filter(or_(*publish_filters))

    items = query.order_by(Course.course_id, Score.exam_date).all()

    show_subject_scores = not display_override or display_override.get('show_subject_scores', True)
    scores_list = []
    for s in items:
        if not show_subject_scores:
            continue
        scores_list.append({
            'score_id': s.score_id,
            'course_id': s.course_id,
            'course_name': s.course_name,
            'term': s.term,
            'score': float(s.score),
            'exam_date': s.exam_date.strftime('%Y-%m-%d') if s.exam_date else None,
            'exam_batch': s.exam_batch,
            'total_score': float(s.total_score) if s.total_score is not None else None,
            'avg_score': float(s.avg_score) if s.avg_score is not None else None,
            'rank_no': s.rank_no,
            'level_tag': s.level_tag,
            'comment_text': s.comment_text,
            'stat_version': s.stat_version,
        })

    summary = _build_my_exam_summary(
            student_id,
            class_name=student.class_name,
            term=filters.get('term'),
            exam_batch=filters.get('exam_batch'),
    )
    if summary and display_override and not display_override.get('show_subject_scores', True):
        summary = {**summary, 'subjects': []}
    return _my_scores_response(
        student,
        scores_list,
        summary,
        display_override,
        compatibility_mode=False,
    )


def get_my_score_options(student_id):
    """返回当前学生实际有成绩的学期、考试批次和课程选项。"""
    from app.services import exam_publish_service
    published_settings = exam_publish_service.get_published_settings_for_student(student_id)
    if not published_settings:
        return {'terms': [], 'exam_batches': [], 'courses': []}

    records = db.session.query(
        Course.term,
        Score.exam_batch,
        Score.course_id,
        Course.course_name,
    ).join(
        Course, Score.course_id == Course.course_id
    ).filter(
        Score.student_id == student_id,
        Score.status == 1,
    ).order_by(
        Course.term,
        Score.exam_batch,
        Course.course_id,
    ).all()
    allowed = {(setting.term, setting.exam_batch) for setting in published_settings}
    records = [row for row in records if (row.term, row.exam_batch) in allowed]

    terms = _unique_options(
        (record.term, record.term)
        for record in records
        if record.term
    )
    exam_batches = _unique_options(
        (record.exam_batch, record.exam_batch)
        for record in records
        if record.exam_batch
    )
    courses = _unique_options(
        (
            f"{record.course_name}（{record.course_id}）" if record.course_name else record.course_id,
            record.course_id,
        )
        for record in records
        if record.course_id
    )

    return {
        'terms': terms,
        'exam_batches': exam_batches,
        'courses': courses,
    }


def soft_delete_score(score_id, operator_id, trace_id, current_user):
    """逻辑删除成绩（status 设为 0）"""
    record = Score.query.filter_by(score_id=score_id).first()
    if not record:
        raise BusinessError(ErrorCode.STUDENT_NOT_FOUND, '成绩记录不存在',
                            data={'score_id': score_id})
    teacher_scope_service.ensure_access(
        current_user, student_id=record.student_id, course_id=record.course_id,
    )

    try:
        record.status = 0
        record.stat_version = 0
        db.session.flush()

        audit_service.write(
            action='score.delete',
            operator_id=operator_id,
            target_type='score',
            target_id=score_id,
            detail={'student_id': record.student_id, 'course_id': record.course_id},
            trace_id=trace_id,
        )

        db.session.commit()
        return {'score_id': score_id, 'task_status': 'deleted'}
    except BusinessError:
        db.session.rollback()
        raise
    except Exception as e:
        db.session.rollback()
        logger.error(f'成绩删除失败: {e}', exc_info=True)
        raise BusinessError(ErrorCode.DB_TRANSACTION_FAILED, '数据库事务失败')


# ========== 内部辅助函数 ==========

def _validate_required_fields(data, fields):
    """校验必填字段"""
    if not data:
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, '请求体不能为空')
    missing = [f for f in fields if f not in data or data[f] is None or str(data[f]).strip() == '']
    if missing:
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, f'缺少必填字段: {", ".join(missing)}')


def _validate_score(value):
    """校验并转换分数"""
    try:
        score = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise BusinessError(ErrorCode.SCORE_OUT_OF_RANGE, '分数必须为数字')
    if score < 0 or score > 100:
        raise BusinessError(ErrorCode.SCORE_OUT_OF_RANGE, '分数必须在 0 到 100 之间')
    return score


def _parse_date(value):
    """解析日期字符串"""
    if isinstance(value, datetime):
        return value.date()
    try:
        return datetime.strptime(str(value), '%Y-%m-%d').date()
    except (ValueError, TypeError):
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, '日期格式必须为 YYYY-MM-DD')


def _my_scores_response(student, scores_list, summary, display_override=None, compatibility_mode=True):
    display_settings = {
        'show_total': config_loader.get_bool('score_display.show_total', True),
        'show_rank': config_loader.get_bool('score_display.show_rank', True),
        'show_class_stats': config_loader.get_bool('score_display.show_class_stats', True),
        'show_warning': config_loader.get_bool('score_display.show_warning', True),
        'show_grade_rank': True,
        'show_class_average': True,
        'show_subject_scores': True,
    }
    if display_override:
        display_settings.update({
            'show_total': display_override.get('show_total', True),
            'show_rank': display_override.get('show_rank', True),
            'show_grade_rank': display_override.get('show_grade_rank', True),
            'show_class_average': display_override.get('show_class_average', True),
            'show_subject_scores': display_override.get('show_subject_scores', True),
        })

    return {
        'student_id': student.user_id,
        'student_name': student.real_name,
        'class_name': student.class_name,
        'scores': scores_list,
        'summary': summary,
        'display_settings': display_settings,
        'compatibility_mode': compatibility_mode,
        'task_status': 'pending_stats',
    }


def _resolve_course_id(course_input):
    """支持课程编号或课程名称查询，例如 CHN01 或 语文。"""
    keyword = str(course_input or '').strip()
    if not keyword:
        return None

    exact_id = db.session.query(Course.course_id).filter(
        Course.course_id == keyword,
        Course.status == 1,
    ).first()
    if exact_id:
        return exact_id.course_id

    exact_name = db.session.query(Course.course_id).filter(
        Course.course_name == keyword,
        Course.status == 1,
    ).first()
    if exact_name:
        return exact_name.course_id

    fuzzy_name = db.session.query(Course.course_id).filter(
        Course.course_name.like(f"%{keyword}%"),
        Course.status == 1,
    ).order_by(Course.course_id).first()
    if fuzzy_name:
        return fuzzy_name.course_id

    raise BusinessError(
        ErrorCode.COURSE_NOT_FOUND,
        '未找到该课程，请检查课程号或课程名称',
        data={'course': keyword},
    )


def _build_my_exam_summary(student_id, class_name=None, term=None, exam_batch=None):
    """构建学生端学期+批次总览。未指定考试批次时不做全库排名聚合。"""
    if not exam_batch:
        return None

    query = db.session.query(
        Score.student_id,
        User.real_name,
        User.class_name,
        Score.course_id,
        Course.course_name,
        Course.term,
        Score.score,
    ).join(
        User, Score.student_id == User.user_id
    ).join(
        Course, Score.course_id == Course.course_id
    ).filter(
        Score.status == 1,
        User.status == 1,
        Score.exam_batch == exam_batch,
    )

    if term:
        query = query.filter(Course.term == term)

    rows = query.order_by(User.class_name, Score.student_id, Course.course_id).all()
    grouped = {}
    for row in rows:
        item = grouped.setdefault(row.student_id, {
            'student_id': row.student_id,
            'student_name': row.real_name or row.student_id,
            'class_name': row.class_name,
            'subjects': [],
        })
        item['subjects'].append({
            'course_id': row.course_id,
            'course_name': row.course_name or row.course_id,
            'score': float(row.score),
        })

    items = []
    for item in grouped.values():
        subject_scores = [subject['score'] for subject in item['subjects']]
        if not subject_scores:
            continue
        item['subject_count'] = len(subject_scores)
        item['total_score'] = round(sum(subject_scores), 2)
        item['average_score'] = round(item['total_score'] / item['subject_count'], 2)
        items.append(item)

    _assign_competition_rank(items, 'total_score', 'overall_rank')

    class_items = [item for item in items if (item.get('class_name') or '') == (class_name or '')]
    _assign_competition_rank(class_items, 'total_score', 'class_rank')

    current = next((item for item in items if item['student_id'] == student_id), None)
    if not current:
        return None

    weak_subject = min(current['subjects'], key=lambda s: s.get('score', 0)) if current.get('subjects') else None
    weak_subject_name = ''
    if weak_subject:
        weak_subject_name = weak_subject.get('course_name') or weak_subject.get('course_id') or '未知科目'

    current['term'] = term
    current['exam_batch'] = exam_batch
    current['grade_rank'] = current.get('overall_rank')
    current['rank_no'] = current.get('overall_rank')
    current['weak_subject'] = weak_subject
    current['weak_subject_tip'] = f"{weak_subject_name} 相对薄弱，可优先复习" if weak_subject else ''
    return current


def _assign_competition_rank(items, score_key, rank_key):
    items.sort(key=lambda item: (-item.get(score_key, 0), item.get('student_id') or ''))
    last_score = None
    last_rank = 0
    for index, item in enumerate(items, start=1):
        score = item.get(score_key, 0)
        if last_score is None or score != last_score:
            last_rank = index
            last_score = score
        item[rank_key] = last_rank


def _unique_options(items):
    seen = set()
    result = []
    for label, value in items:
        if value is None or value == '':
            continue
        key = str(value)
        if key in seen:
            continue
        seen.add(key)
        result.append({'label': str(label), 'value': key})
    return result
