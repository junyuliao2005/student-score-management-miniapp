"""统计分析服务：总分、平均分、排名、等级、评语、统计总览"""
import logging
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime

from app.extensions import db
from app.models.score import Score
from app.models.user import User
from app.models.course import Course
from app.services import config_loader, comment_service, warning_calculator
from app.utils.ranking import competition_rank
from app.utils.errors import BusinessError, ErrorCode
from app.utils.validators import validate_pagination

logger = logging.getLogger(__name__)

# 等级规则默认值
DEFAULT_LEVEL_RANGES = {
    '优秀': [90, 100],
    '良好': [80, 89.99],
    '中等': [70, 79.99],
    '及格': [60, 69.99],
    '不及格': [0, 59.99],
}


def refresh_student_derived(student_id, term, session=None):
    """
    刷新单个学生某学期的派生统计字段。
    计算：total_score, avg_score, level_tag, comment_text, stat_version
    写回该学生该学期全部成绩记录。
    """
    records = Score.query.filter_by(student_id=student_id, status=1) \
        .join(Course, Score.course_id == Course.course_id) \
        .filter(Course.term == term) \
        .all()

    if not records:
        raise BusinessError(ErrorCode.STUDENT_NOT_FOUND, '该学生该学期无有效成绩',
                            data={'student_id': student_id})

    # 计算总分和平均分
    scores_list = [float(r.score) for r in records]
    total_score = sum(scores_list)
    valid_count = len(scores_list)
    avg_score = round(total_score / valid_count, 2)

    # 等级评定
    level_tag = _map_level(avg_score)

    # 预警计算（用于评语）
    warnings = warning_calculator.build_warnings(student_id, term)

    # 自动评语
    comment_text = comment_service.build_comment(avg_score, level_tag, warnings)

    # 获取当前最大 stat_version 并 +1
    current_version = max((r.stat_version or 0) for r in records)
    next_version = current_version + 1

    # 写回所有记录
    for r in records:
        r.total_score = Decimal(str(total_score))
        r.avg_score = Decimal(str(avg_score))
        r.level_tag = level_tag
        r.comment_text = comment_text
        r.stat_version = next_version

    db.session.flush()
    return next_version


def refresh_rankings(term, course_id=None, class_name=None, session=None):
    """
    刷新排名。
    按班级分组（如果指定），否则按学期全局排名。
    采用竞赛排名法：同分同名次，下一名跳过。
    """
    # 查询所有需要排名的学生
    query = db.session.query(
        Score.student_id,
        db.func.max(Score.total_score).label('total_score'),
        db.func.max(Score.avg_score).label('avg_score'),
    ).join(Course, Score.course_id == Course.course_id) \
        .filter(Score.status == 1, Course.term == term)

    if course_id:
        query = query.filter(Score.course_id == course_id)
    if class_name:
        query = query.join(User, Score.student_id == User.user_id) \
            .filter(User.class_name == class_name)

    query = query.group_by(Score.student_id)
    rows = query.all()

    # 构造排名数据
    items = []
    for row in rows:
        items.append({
            'student_id': row.student_id,
            'total_score': float(row.total_score) if row.total_score else 0,
            'avg_score': float(row.avg_score) if row.avg_score else 0,
        })

    # 竞赛排名
    competition_rank(items, score_key='total_score')

    # 写回排名到 scores 表（安全写法：逐学生更新，避免 join().update()）
    for item in items:
        # 先查出该学生该学期所有有效成绩记录的主键
        id_query = db.session.query(Score.score_id). \
            join(Course, Score.course_id == Course.course_id). \
            filter(
                Score.student_id == item['student_id'],
                Score.status == 1,
                Course.term == term,
            )
        if course_id:
            id_query = id_query.filter(Score.course_id == course_id)
        if class_name:
            id_query = id_query.join(User, Score.student_id == User.user_id). \
                filter(User.class_name == class_name)

        score_ids = [row[0] for row in id_query.all()]

        if score_ids:
            Score.query.filter(Score.score_id.in_(score_ids)).update(
                {'rank_no': item['rank_no']}, synchronize_session=False
            )

    db.session.flush()
    return len(items)


def get_overview(term=None, course_id=None, class_name=None):
    """
    统计总览：返回平均分、优秀率、及格率、低分人数等。
    """
    low_threshold = config_loader.get_int('warning.low_score.threshold', 60)

    query = db.session.query(
        db.func.count(Score.score_id).label('score_count'),
        db.func.count(db.distinct(Score.student_id)).label('student_count'),
        db.func.avg(Score.score).label('avg_score'),
        db.func.max(Score.score).label('max_score'),
        db.func.min(Score.score).label('min_score'),
        db.func.sum(db.case((Score.score >= 90, 1), else_=0)).label('excellent_count'),
        db.func.sum(db.case((Score.score >= 60, 1), else_=0)).label('pass_count'),
        db.func.sum(db.case((Score.score < low_threshold, 1), else_=0)).label('low_count'),
    ).select_from(Score).join(
        Course, Score.course_id == Course.course_id
    ).filter(Score.status == 1)

    if term:
        query = query.filter(Course.term == term)
    if course_id:
        query = query.filter(Score.course_id == course_id)
    if class_name:
        query = query.join(User, Score.student_id == User.user_id).filter(User.class_name == class_name)

    row = query.one()
    total = int(row.score_count or 0)

    if not total:
        return {
            'student_count': 0,
            'score_count': 0,
            'avg_score': 0,
            'max_score': 0,
            'min_score': 0,
            'excellent_rate': 0,
            'pass_rate': 0,
            'low_score_count': 0,
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }

    return {
        'student_count': int(row.student_count or 0),
        'score_count': total,
        'avg_score': round(float(row.avg_score or 0), 2),
        'max_score': float(row.max_score or 0),
        'min_score': float(row.min_score or 0),
        'excellent_rate': round(int(row.excellent_count or 0) / total, 2),
        'pass_rate': round(int(row.pass_count or 0) / total, 2),
        'low_score_count': int(row.low_count or 0),
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }


def get_rankings(term=None, course_id=None, class_name=None, exam_batch=None, page=1, page_size=20):
    """
    查询排名列表。
    返回每个学生的 student_id, student_name, total_score, avg_score, rank_no, level_tag, comment_text。
    """
    page, page_size = validate_pagination({'page': page, 'page_size': page_size})

    if not exam_batch:
        return _empty_paged_result(page, page_size, '请先选择考试批次后再查看排名')

    all_items = _query_total_rank_items(term=term, exam_batch=exam_batch, class_name=class_name, course_id=course_id)
    competition_rank(all_items, score_key='total_score')
    for item in all_items:
        item['avg_score'] = item.get('average_score', 0)
        item['rank_no'] = item.get('rank_no')
    all_items.sort(key=lambda x: (x.get('rank_no') or 999999, -x.get('total_score', 0), x['student_id']))

    total = len(all_items)
    start = (page - 1) * page_size
    end = start + page_size
    paged = all_items[start:end]

    result_list = []
    for row in paged:
        result_list.append({
            'student_id': row['student_id'],
            'student_name': row['student_name'],
            'class_name': row['class_name'],
            'total_score': row['total_score'],
            'avg_score': row['avg_score'],
            'rank_no': row['rank_no'],
            'level_tag': row['level_tag'],
            'comment_text': row['comment_text'],
        })

    return {
        'list': result_list,
        'page': page,
        'page_size': page_size,
        'total': total,
        'total_pages': (total + page_size - 1) // page_size,
    }


def get_total_rankings(term=None, exam_batch=None, class_name=None, page=1, page_size=20):
    """实时聚合总分排名，不写回数据库。"""
    page, page_size = validate_pagination({'page': page, 'page_size': page_size})
    if not exam_batch:
        return _empty_paged_result(page, page_size, '请先选择考试批次后再查看总分排名')

    items = _build_total_ranking_items(term=term, exam_batch=exam_batch, class_name=class_name)

    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    paged = items[start:end]
    _attach_subjects(paged, term=term, exam_batch=exam_batch)
    return {
        'list': paged,
        'page': page,
        'page_size': page_size,
        'total': total,
        'total_pages': (total + page_size - 1) // page_size,
    }


def get_subject_rankings(term=None, exam_batch=None, course_id=None, class_name=None, page=1, page_size=20):
    """单科排名：按指定考试批次和课程分页返回分数排名。"""
    page, page_size = validate_pagination({'page': page, 'page_size': page_size})
    if not exam_batch:
        return _empty_paged_result(page, page_size, '请先选择考试批次后再查看单科排名')
    if not course_id:
        return _empty_paged_result(page, page_size, '请先选择课程后再查看单科排名')

    resolved_course_id = _resolve_course_id(course_id)
    query = db.session.query(
        Score.student_id,
        User.real_name.label('student_name'),
        User.class_name,
        Score.course_id,
        Course.course_name,
        Score.score,
    ).join(
        User, Score.student_id == User.user_id
    ).join(
        Course, Score.course_id == Course.course_id
    ).filter(
        Score.status == 1,
        User.status == 1,
        Score.exam_batch == exam_batch,
        Score.course_id == resolved_course_id,
    )

    if term:
        query = query.filter(Course.term == term)
    if class_name:
        query = query.filter(User.class_name == class_name)

    items = []
    for row in query.order_by(Score.score.desc(), Score.student_id).all():
        items.append({
            'student_id': row.student_id,
            'student_name': row.student_name or row.student_id,
            'class_name': row.class_name,
            'grade_name': _parse_grade_name(row.class_name),
            'course_id': row.course_id,
            'course_name': row.course_name or row.course_id,
            'score': float(row.score),
        })

    competition_rank(items, score_key='score')
    for item in items:
        item['overall_rank'] = item.get('rank_no')

    by_class = {}
    by_grade = {}
    for item in items:
        by_class.setdefault(item.get('class_name') or '', []).append(item)
        by_grade.setdefault(item.get('grade_name') or '未知年级', []).append(item)

    for class_items in by_class.values():
        competition_rank(class_items, score_key='score')
        for item in class_items:
            item['class_rank'] = item.get('rank_no')
            item['rank_no'] = item.get('overall_rank')

    for grade_items in by_grade.values():
        competition_rank(grade_items, score_key='score')
        for item in grade_items:
            item['grade_rank'] = item.get('rank_no')
            item['rank_no'] = item.get('overall_rank')

    items.sort(key=lambda x: (x.get('overall_rank') or 999999, -x.get('score', 0), x['student_id']))
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        'list': items[start:end],
        'page': page,
        'page_size': page_size,
        'total': total,
        'total_pages': (total + page_size - 1) // page_size,
    }


def get_honor_roll(term=None, exam_batch=None, class_name=None):
    """荣誉榜：总分前 10、单科第一、优秀学生。"""
    if not exam_batch:
        return {
            'top_total': [],
            'subject_best': [],
            'excellent_students': [],
            'message': '请先选择考试批次后再查看荣誉榜',
        }

    items = _build_total_ranking_items(term=term, exam_batch=exam_batch, class_name=class_name)
    top_total = items[:10]
    _attach_subjects(top_total, term=term, exam_batch=exam_batch)
    excellent_students = [
        item for item in items
        if item.get('average_score', 0) >= 90 or (item.get('overall_rank') or 999999) <= 10
    ][:10]
    _attach_subjects(excellent_students, term=term, exam_batch=exam_batch)

    subject_best_map = {}
    query = db.session.query(
        Score.course_id,
        Course.course_name,
        Score.student_id,
        User.real_name.label('student_name'),
        User.class_name,
        Score.score,
    ).join(
        User, Score.student_id == User.user_id
    ).join(
        Course, Score.course_id == Course.course_id
    ).filter(Score.status == 1)

    if term:
        query = query.filter(Course.term == term)
    if exam_batch:
        query = query.filter(Score.exam_batch == exam_batch)
    if class_name:
        query = query.filter(User.class_name == class_name)

    for row in query.all():
        current = subject_best_map.get(row.course_id)
        score_value = float(row.score)
        if current is None or score_value > current['score']:
            subject_best_map[row.course_id] = {
                'course_id': row.course_id,
                'course_name': row.course_name or row.course_id,
                'student_id': row.student_id,
                'student_name': row.student_name or row.student_id,
                'class_name': row.class_name,
                'score': score_value,
            }

    subject_best = sorted(subject_best_map.values(), key=lambda x: x['course_id'])
    return {
        'top_total': top_total,
        'subject_best': subject_best,
        'excellent_students': excellent_students,
    }


def get_student_total_summary(student_id, term=None, exam_batch=None):
    """学生端总分/平均分/排名汇总。"""
    if not exam_batch:
        return None

    student = db.session.query(User.user_id).filter(User.user_id == student_id, User.status == 1).first()
    if not student:
        return None

    items = _build_total_ranking_items(term=term, exam_batch=exam_batch, class_name=None)
    current = next((item for item in items if item['student_id'] == student_id), None)
    if not current:
        return None

    weak_subject = None
    subjects = current.get('subjects') or []
    if subjects:
        weak_subject = min(subjects, key=lambda s: s.get('score', 0))
    weak_subject_name = ''
    if weak_subject:
        weak_subject_name = weak_subject.get('course_name') or weak_subject.get('course_id') or '未知科目'

    return {
        **current,
        'term': term,
        'exam_batch': exam_batch,
        'weak_subject': weak_subject,
        'weak_subject_tip': f"{weak_subject_name} 相对薄弱，可优先复习" if weak_subject else '',
    }


def _build_total_ranking_items(term=None, exam_batch=None, class_name=None):
    if not exam_batch:
        return []

    items = _query_total_rank_items(term=term, exam_batch=exam_batch, class_name=class_name)

    competition_rank(items, score_key='total_score')
    for item in items:
        item['overall_rank'] = item.get('rank_no')
        item['grade_rank'] = item.get('rank_no')

    by_class = {}
    by_grade = {}
    for item in items:
        by_class.setdefault(item.get('class_name') or '', []).append(item)
        by_grade.setdefault(item.get('grade_name') or '未知年级', []).append(item)
    for class_items in by_class.values():
        competition_rank(class_items, score_key='total_score')
        for item in class_items:
            item['class_rank'] = item.get('rank_no')
            item['rank_no'] = item.get('overall_rank')
    for grade_items in by_grade.values():
        competition_rank(grade_items, score_key='total_score')
        for item in grade_items:
            item['grade_rank'] = item.get('rank_no')
            item['rank_no'] = item.get('overall_rank')

    items.sort(key=lambda x: (x.get('overall_rank') or 999999, -x.get('total_score', 0), x['student_id']))
    return items


def _empty_paged_result(page, page_size, message):
    return {
        'list': [],
        'page': page,
        'page_size': page_size,
        'total': 0,
        'total_pages': 0,
        'message': message,
    }


def _query_total_rank_items(term=None, exam_batch=None, class_name=None, course_id=None):
    """按学生聚合总分/均分，只查询必要字段，不加载模型关系。"""
    query = db.session.query(
        Score.student_id,
        User.real_name.label('student_name'),
        User.class_name,
        db.func.sum(Score.score).label('total_score'),
        db.func.avg(Score.score).label('average_score'),
        db.func.count(Score.score_id).label('subject_count'),
        db.func.max(Score.level_tag).label('level_tag'),
        db.func.max(Score.comment_text).label('comment_text'),
    ).join(
        User, Score.student_id == User.user_id
    ).join(
        Course, Score.course_id == Course.course_id
    ).filter(
        Score.status == 1,
        User.status == 1,
    )

    if term:
        query = query.filter(Course.term == term)
    if exam_batch:
        query = query.filter(Score.exam_batch == exam_batch)
    if class_name:
        query = query.filter(User.class_name == class_name)
    if course_id:
        query = query.filter(Score.course_id == course_id)

    rows = query.group_by(
        Score.student_id,
        User.real_name,
        User.class_name,
    ).all()

    return [
        {
            'student_id': row.student_id,
            'student_name': row.student_name or row.student_id,
            'class_name': row.class_name,
            'grade_name': _parse_grade_name(row.class_name),
            'total_score': round(float(row.total_score or 0), 2),
            'average_score': round(float(row.average_score or 0), 2),
            'subject_count': int(row.subject_count or 0),
            'level_tag': row.level_tag,
            'comment_text': row.comment_text,
            'subjects': [],
        }
        for row in rows
    ]


def _attach_subjects(items, term=None, exam_batch=None):
    """只为当前页/小列表补充科目明细，避免总分排名拉取全量明细。"""
    if not items:
        return

    item_map = {item['student_id']: item for item in items}
    student_ids = list(item_map.keys())
    query = db.session.query(
        Score.student_id,
        Score.course_id,
        Course.course_name,
        Score.score,
    ).join(
        Course, Score.course_id == Course.course_id
    ).filter(
        Score.status == 1,
        Score.student_id.in_(student_ids),
    )

    if term:
        query = query.filter(Course.term == term)
    if exam_batch:
        query = query.filter(Score.exam_batch == exam_batch)

    for item in items:
        item['subjects'] = []

    for row in query.order_by(Score.student_id, Course.course_id).all():
        item = item_map.get(row.student_id)
        if not item:
            continue
        item['subjects'].append({
            'course_id': row.course_id,
            'course_name': row.course_name or row.course_id,
            'score': float(row.score),
        })


def _resolve_course_id(course_input):
    """支持课程编号、课程名称和模糊课程名。"""
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


def _parse_grade_name(class_name):
    text = str(class_name or '').strip()
    if not text:
        return '未知年级'
    for grade in ('初一', '初二', '初三', '高一', '高二', '高三'):
        if text.startswith(grade):
            return grade
    return '未知年级'


def evaluate_scores(term=None, class_name=None, course_id=None, operator_id=None, trace_id=None):
    """
    手动触发等级评定、评语刷新和排名刷新。
    1. 找到所有需要刷新的学生
    2. 逐学生刷新派生字段
    3. 刷新排名
    """
    # 找到所有有成绩的学生
    query = db.session.query(Score.student_id).filter(Score.status == 1)
    if term:
        query = query.join(Course, Score.course_id == Course.course_id).filter(Course.term == term)
    if course_id:
        query = query.filter(Score.course_id == course_id)
    if class_name:
        query = query.join(User, Score.student_id == User.user_id).filter(User.class_name == class_name)

    student_ids = list(set([row[0] for row in query.all()]))

    if not student_ids:
        return {
            'refreshed_students': 0,
            'refreshed_records': 0,
            'task_status': 'done',
            'refreshed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }

    # 刷新每个学生的派生字段
    refreshed_records = 0
    for sid in student_ids:
        if term:
            version = refresh_student_derived(sid, term)
            records = Score.query.filter_by(student_id=sid, status=1) \
                .join(Course, Score.course_id == Course.course_id) \
                .filter(Course.term == term).all()
            refreshed_records += len(records)
        else:
            # 如果没指定学期，刷新所有学期
            terms = db.session.query(Course.term).join(Score, Score.course_id == Course.course_id) \
                .filter(Score.student_id == sid, Score.status == 1).distinct().all()
            for t in terms:
                refresh_student_derived(sid, t[0])
                records = Score.query.filter_by(student_id=sid, status=1) \
                    .join(Course, Score.course_id == Course.course_id) \
                    .filter(Course.term == t[0]).all()
                refreshed_records += len(records)

    # 刷新排名
    rank_count = refresh_rankings(term=term or '', course_id=course_id, class_name=class_name)

    db.session.commit()

    return {
        'refreshed_students': len(student_ids),
        'refreshed_records': refreshed_records,
        'rank_count': rank_count,
        'task_status': 'done',
        'refreshed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }


# ========== 内部辅助函数 ==========

def _map_level(avg_score):
    """根据平均分映射等级标签"""
    try:
        ranges = config_loader.get_json('grade.level.ranges')
    except Exception:
        ranges = DEFAULT_LEVEL_RANGES

    if not ranges:
        ranges = DEFAULT_LEVEL_RANGES

    for level, (low, high) in ranges.items():
        if low <= avg_score <= high:
            return level

    return '不及格'
