"""Lightweight, explicitly filtered analytics for teacher/admin dashboards."""
from sqlalchemy import and_, case, or_

from app.extensions import db
from app.models.course import Course
from app.models.score import Score
from app.models.user import User
from app.services import teacher_scope_service, exam_publish_service
from app.utils.errors import BusinessError, ErrorCode
from app.utils.validators import validate_pagination


def get_trend(current_user, term=None, class_name=None, course_id=None, student_id=None):
    if not student_id and not class_name:
        raise BusinessError(ErrorCode.INVALID_PARAMETER, '请选择学生或班级后查看趋势')
    if student_id:
        teacher_scope_service.ensure_access(current_user, student_id=student_id, course_id=course_id)
    elif class_name:
        teacher_scope_service.ensure_access(current_user, class_name=class_name, course_id=course_id)

    query = db.session.query(
        Score.exam_batch,
        db.func.min(Score.exam_date).label('exam_date'),
        db.func.avg(Score.score).label('average_score'),
        db.func.count(Score.score_id).label('score_count'),
    ).select_from(Score).join(
        User, Score.student_id == User.user_id
    ).join(
        Course, Score.course_id == Course.course_id
    ).filter(Score.status == 1, User.status == 1)
    query = teacher_scope_service.apply_score_scope(query, current_user)
    if term:
        query = query.filter(Course.term == term)
    if class_name:
        query = query.filter(User.class_name == class_name)
    if course_id:
        query = query.filter(Score.course_id == course_id)
    if student_id:
        query = query.filter(Score.student_id == student_id)
    rows = query.group_by(Score.exam_batch).order_by(db.func.min(Score.exam_date), Score.exam_batch).limit(50).all()
    return {
        'series': [
            {
                'exam_batch': row.exam_batch,
                'exam_date': row.exam_date.strftime('%Y-%m-%d') if row.exam_date else None,
                'average_score': round(float(row.average_score or 0), 2),
                'score_count': int(row.score_count or 0),
            }
            for row in rows
        ],
        'scope': 'student' if student_id else 'class',
    }


def get_my_trend(student_id, term=None, course_id=None):
    settings = exam_publish_service.get_published_settings_for_student(
        student_id, {'term': term} if term else {},
    )
    visible_pairs = {
        (setting.term, setting.exam_batch)
        for setting in settings
        if setting.show_subject_scores
    }
    if not visible_pairs:
        return {'series': [], 'scope': 'student'}
    query = db.session.query(
        Score.exam_batch,
        db.func.min(Score.exam_date).label('exam_date'),
        db.func.avg(Score.score).label('average_score'),
        db.func.count(Score.score_id).label('score_count'),
    ).join(Course, Score.course_id == Course.course_id).filter(
        Score.student_id == student_id,
        Score.status == 1,
        or_(*[
            and_(Course.term == visible_term, Score.exam_batch == visible_batch)
            for visible_term, visible_batch in visible_pairs
        ]),
    )
    if term:
        query = query.filter(Course.term == term)
    if course_id:
        query = query.filter(Score.course_id == course_id)
    rows = query.group_by(Score.exam_batch).order_by(db.func.min(Score.exam_date), Score.exam_batch).limit(50).all()
    return {
        'series': [
            {
                'exam_batch': row.exam_batch,
                'exam_date': row.exam_date.strftime('%Y-%m-%d') if row.exam_date else None,
                'average_score': round(float(row.average_score or 0), 2),
                'score_count': int(row.score_count or 0),
            }
            for row in rows
        ],
        'scope': 'student',
    }


def get_distribution(current_user, term=None, exam_batch=None, class_name=None, course_id=None):
    if not exam_batch:
        raise BusinessError(ErrorCode.INVALID_PARAMETER, '请先选择考试批次后查看分数段')
    query = db.session.query(
        db.func.count(Score.score_id).label('total'),
        db.func.sum(case((Score.score < 60, 1), else_=0)).label('under_60'),
        db.func.sum(case((and_(Score.score >= 60, Score.score < 70), 1), else_=0)).label('s60_69'),
        db.func.sum(case((and_(Score.score >= 70, Score.score < 80), 1), else_=0)).label('s70_79'),
        db.func.sum(case((and_(Score.score >= 80, Score.score < 90), 1), else_=0)).label('s80_89'),
        db.func.sum(case((Score.score >= 90, 1), else_=0)).label('s90_100'),
    ).select_from(Score).join(User, Score.student_id == User.user_id) \
        .join(Course, Score.course_id == Course.course_id) \
        .filter(Score.status == 1, User.status == 1, Score.exam_batch == exam_batch)
    query = teacher_scope_service.apply_score_scope(query, current_user)
    if term:
        query = query.filter(Course.term == term)
    if class_name:
        query = query.filter(User.class_name == class_name)
    if course_id:
        query = query.filter(Score.course_id == course_id)
    row = query.one()
    total = int(row.total or 0)
    values = [
        ('0-59', int(row.under_60 or 0)),
        ('60-69', int(row.s60_69 or 0)),
        ('70-79', int(row.s70_79 or 0)),
        ('80-89', int(row.s80_89 or 0)),
        ('90-100', int(row.s90_100 or 0)),
    ]
    return {
        'total': total,
        'segments': [
            {'label': label, 'count': count, 'rate': round(count / total, 4) if total else 0}
            for label, count in values
        ],
    }


def get_progress_rankings(current_user, term, baseline_batch, current_batch, class_name=None,
                          page=1, page_size=20):
    if not term or not baseline_batch or not current_batch:
        raise BusinessError(ErrorCode.INVALID_PARAMETER, '请选择学期、基准批次和当前批次')
    if baseline_batch == current_batch:
        raise BusinessError(ErrorCode.INVALID_PARAMETER, '基准批次和当前批次不能相同')
    page, page_size = validate_pagination({'page': page, 'page_size': page_size})

    grouped = db.session.query(
        Score.student_id.label('student_id'),
        User.real_name.label('student_name'),
        User.class_name.label('class_name'),
        db.func.avg(case((Score.exam_batch == baseline_batch, Score.score), else_=None)).label('baseline_score'),
        db.func.avg(case((Score.exam_batch == current_batch, Score.score), else_=None)).label('current_score'),
    ).select_from(Score).join(User, Score.student_id == User.user_id) \
        .join(Course, Score.course_id == Course.course_id) \
        .filter(
            Score.status == 1,
            User.status == 1,
            Course.term == term,
            Score.exam_batch.in_([baseline_batch, current_batch]),
        )
    grouped = teacher_scope_service.apply_score_scope(grouped, current_user)
    if class_name:
        grouped = grouped.filter(User.class_name == class_name)
    grouped = grouped.group_by(Score.student_id, User.real_name, User.class_name).having(
        db.func.count(db.distinct(Score.exam_batch)) == 2
    ).subquery()

    delta = (grouped.c.current_score - grouped.c.baseline_score).label('delta')
    ranked = db.session.query(
        grouped.c.student_id,
        grouped.c.student_name,
        grouped.c.class_name,
        grouped.c.baseline_score,
        grouped.c.current_score,
        delta,
        db.func.rank().over(order_by=delta.desc()).label('rank_no'),
    ).subquery()
    total = db.session.query(db.func.count()).select_from(ranked).scalar() or 0
    rows = db.session.query(ranked).order_by(ranked.c.rank_no, ranked.c.student_id) \
        .offset((page - 1) * page_size).limit(page_size).all()
    return {
        'list': [
            {
                'student_id': row.student_id,
                'student_name': row.student_name,
                'class_name': row.class_name,
                'baseline_score': round(float(row.baseline_score or 0), 2),
                'current_score': round(float(row.current_score or 0), 2),
                'delta': round(float(row.delta or 0), 2),
                'rank_no': int(row.rank_no),
            }
            for row in rows
        ],
        'page': page,
        'page_size': page_size,
        'total': int(total),
        'total_pages': (int(total) + page_size - 1) // page_size,
    }


def get_bias_analysis(current_user, term, exam_batch, class_name=None, page=1, page_size=20):
    if not term or not exam_batch:
        raise BusinessError(ErrorCode.INVALID_PARAMETER, '请选择学期和考试批次后查看偏科分析')
    page, page_size = validate_pagination({'page': page, 'page_size': page_size})
    student_query = db.session.query(Score.student_id).select_from(Score) \
        .join(User, Score.student_id == User.user_id) \
        .join(Course, Score.course_id == Course.course_id) \
        .filter(
            Score.status == 1, User.status == 1,
            Course.term == term, Score.exam_batch == exam_batch,
        )
    student_query = teacher_scope_service.apply_score_scope(student_query, current_user)
    if class_name:
        student_query = student_query.filter(User.class_name == class_name)
    student_query = student_query.distinct()
    total = student_query.count()
    student_ids = [row.student_id for row in student_query.order_by(Score.student_id)
                   .offset((page - 1) * page_size).limit(page_size).all()]
    if not student_ids:
        return _empty_page(page, page_size, total)

    rows = db.session.query(
        Score.student_id,
        User.real_name.label('student_name'),
        User.class_name,
        Score.course_id,
        Course.course_name,
        db.func.avg(Score.score).label('average_score'),
    ).join(User, Score.student_id == User.user_id) \
        .join(Course, Score.course_id == Course.course_id) \
        .filter(
            Score.status == 1, Course.term == term, Score.exam_batch == exam_batch,
            Score.student_id.in_(student_ids),
        ).group_by(
            Score.student_id, User.real_name, User.class_name, Score.course_id, Course.course_name,
        ).all()
    grouped = {}
    for row in rows:
        item = grouped.setdefault(row.student_id, {
            'student_id': row.student_id,
            'student_name': row.student_name,
            'class_name': row.class_name,
            'subjects': [],
        })
        item['subjects'].append({
            'course_id': row.course_id,
            'course_name': row.course_name or row.course_id,
            'score': round(float(row.average_score or 0), 2),
        })
    result = []
    for student_id in student_ids:
        item = grouped.get(student_id)
        if not item or len(item['subjects']) < 2:
            continue
        highest = max(item['subjects'], key=lambda subject: subject['score'])
        lowest = min(item['subjects'], key=lambda subject: subject['score'])
        item.update({
            'highest_subject': highest,
            'lowest_subject': lowest,
            'gap': round(highest['score'] - lowest['score'], 2),
        })
        result.append(item)
    return {
        'list': result,
        'page': page,
        'page_size': page_size,
        'total': total,
        'total_pages': (total + page_size - 1) // page_size,
    }


def _empty_page(page, page_size, total=0):
    return {'list': [], 'page': page, 'page_size': page_size, 'total': total,
            'total_pages': (total + page_size - 1) // page_size}
