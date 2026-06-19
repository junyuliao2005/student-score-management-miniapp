"""通用输入选项服务。"""
from app.extensions import db
from app.models.course import Course
from app.models.exam_paper import ExamPaper
from app.models.role import Role
from app.models.score import Score
from app.models.user import User
from app.utils.errors import BusinessError, ErrorCode

DEFAULT_SUBJECTS = ['语文', '数学', '英语', '物理', '化学', '生物', '历史', '地理', '政治', '计算机基础']
DEFAULT_PAPER_TITLES = ['期中试卷', '期末试卷', '月考试卷', '单元测试', '模拟考试', '随堂测验']
DEFAULT_EXAM_BATCHES = ['期中', '期末', '月考', '单元测试', '模拟考试', 'final_test']
DEFAULT_TERMS = ['2025-2026-1', '2025-2026-2']


def get_options(option_type, current_user):
    roles = current_user.get('roles', [])
    user_id = current_user.get('user_id')

    if not option_type:
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, '请选择选项类型')

    if _is_student_only(roles):
        values = _student_options(option_type, user_id)
    else:
        values = _staff_options(option_type)

    return {'options': [{'label': label, 'value': value} for label, value in values]}


def _student_options(option_type, user_id):
    if option_type in ('students', 'student_names', 'teachers'):
        if option_type == 'teachers':
            teachers = User.query.filter(User.status == 1, User.roles.any(Role.role_name == 'teacher')) \
                .order_by(User.user_id).all()
            return [(f'{u.real_name}（{u.user_id}）', u.user_id) for u in teachers]
        user = User.query.filter_by(user_id=user_id, status=1).first()
        if not user:
            return []
        if option_type == 'students':
            return [(f'{user.real_name}（{user.user_id}）', user.user_id)]
        return [(user.real_name, user.real_name)]

    query = Score.query.join(Course, Score.course_id == Course.course_id) \
        .filter(Score.status == 1, Score.student_id == user_id)

    if option_type in ('courses', 'course_ids'):
        courses = [score.course for score in query.all() if score.course]
        if option_type == 'courses':
            return _unique_pairs((f'{c.course_name}（{c.course_id}）', c.course_id) for c in courses)
        return _unique_pairs((c.course_id, c.course_id) for c in courses)
    if option_type == 'terms':
        return _unique_pairs((score.course.term, score.course.term) for score in query.all() if score.course)
    if option_type == 'exam_batches':
        return _unique_pairs((score.exam_batch, score.exam_batch) for score in query.all())
    if option_type == 'classes':
        user = User.query.filter_by(user_id=user_id, status=1).first()
        return [(user.class_name, user.class_name)] if user and user.class_name else []
    if option_type == 'subjects':
        return [(x, x) for x in DEFAULT_SUBJECTS]
    if option_type == 'paper_titles':
        return [(x, x) for x in DEFAULT_PAPER_TITLES]
    return []


def _staff_options(option_type):
    if option_type == 'students':
        users = User.query.filter(User.status == 1, User.roles.any(Role.role_name == 'student')) \
            .order_by(User.user_id).all()
        return [(f'{u.real_name}（{u.user_id}）', u.user_id) for u in users]
    if option_type == 'student_names':
        users = User.query.filter(User.status == 1, User.roles.any(Role.role_name == 'student')) \
            .order_by(User.real_name).all()
        return _unique_pairs((u.real_name, u.real_name) for u in users)
    if option_type == 'teachers':
        users = User.query.filter(User.status == 1, User.roles.any(Role.role_name == 'teacher')) \
            .order_by(User.user_id).all()
        return [(f'{u.real_name}（{u.user_id}）', u.user_id) for u in users]
    if option_type == 'classes':
        rows = db.session.query(User.class_name).filter(User.status == 1, User.class_name.isnot(None)) \
            .filter(db.func.trim(User.class_name) != '').distinct().order_by(User.class_name).all()
        return [(row[0], row[0]) for row in rows]
    if option_type == 'courses':
        courses = Course.query.filter_by(status=1).order_by(Course.course_id).all()
        return [(f'{c.course_name}（{c.course_id}）', c.course_id) for c in courses]
    if option_type == 'course_ids':
        courses = Course.query.filter_by(status=1).order_by(Course.course_id).all()
        return [(c.course_id, c.course_id) for c in courses]
    if option_type == 'terms':
        course_terms = db.session.query(Course.term).filter(Course.term.isnot(None)).distinct().all()
        return _merge_defaults([(row[0], row[0]) for row in course_terms if row[0]], DEFAULT_TERMS)
    if option_type == 'exam_batches':
        score_batches = db.session.query(Score.exam_batch).filter(Score.status == 1).distinct().all()
        return _merge_defaults([(row[0], row[0]) for row in score_batches if row[0]], DEFAULT_EXAM_BATCHES)
    if option_type == 'subjects':
        paper_subjects = db.session.query(ExamPaper.subject).filter(ExamPaper.subject.isnot(None)).distinct().all()
        return _merge_defaults([(row[0], row[0]) for row in paper_subjects if row[0]], DEFAULT_SUBJECTS)
    if option_type == 'paper_titles':
        titles = db.session.query(ExamPaper.title).filter(ExamPaper.title.isnot(None)).distinct().all()
        return _merge_defaults([(row[0], row[0]) for row in titles if row[0]], DEFAULT_PAPER_TITLES)
    return []


def _is_student_only(roles):
    return 'student' in roles and 'teacher' not in roles and 'admin' not in roles


def _merge_defaults(values, defaults):
    merged = list(values) + [(item, item) for item in defaults]
    return _unique_pairs(merged)


def _unique_pairs(values):
    seen = set()
    result = []
    for label, value in values:
        if value is None or value == '':
            continue
        key = str(value)
        if key in seen:
            continue
        seen.add(key)
        result.append((str(label), key))
    return result
