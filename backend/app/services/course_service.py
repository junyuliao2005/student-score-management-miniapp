"""课程管理服务"""
from app.extensions import db
from app.models.course import Course
from app.models.user import User
from app.utils.errors import BusinessError, ErrorCode
from app.utils.validators import validate_pagination


def list_courses(page=1, page_size=20, keyword=None, term=None, teacher_id=None):
    """分页查询课程"""
    page, page_size = validate_pagination({'page': page, 'page_size': page_size})

    query = Course.query
    if keyword:
        like = f'%{keyword}%'
        query = query.filter(
            db.or_(Course.course_name.like(like), Course.course_id.like(like))
        )
    if term:
        query = query.filter_by(term=term)
    if teacher_id:
        query = query.filter_by(teacher_id=teacher_id)

    total = query.count()
    items = query.order_by(Course.created_at.desc()) \
        .offset((page - 1) * page_size) \
        .limit(page_size) \
        .all()

    return {
        'list': [c.to_dict() for c in items],
        'page': page,
        'page_size': page_size,
        'total': total,
    }


def create_course(course_id, course_name, teacher_id, term, credit=None):
    """新增课程"""
    if Course.query.filter_by(course_id=course_id).first():
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, f'课程ID {course_id} 已存在')
    if Course.query.filter_by(course_name=course_name).first():
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, f'课程名 {course_name} 已存在')

    # 验证教师存在
    teacher = User.query.filter_by(user_id=teacher_id).first()
    if not teacher:
        raise BusinessError(ErrorCode.STUDENT_NOT_FOUND, '教师用户不存在')

    course = Course(
        course_id=course_id,
        course_name=course_name,
        teacher_id=teacher_id,
        term=term,
        credit=credit,
        status=1,
    )
    db.session.add(course)
    db.session.commit()
    return course.to_dict()


def update_course(course_id, **kwargs):
    """修改课程信息"""
    course = Course.query.filter_by(course_id=course_id).first()
    if not course:
        raise BusinessError(ErrorCode.COURSE_NOT_FOUND, '课程不存在')

    allowed_fields = ['course_name', 'teacher_id', 'term', 'credit', 'status']
    for field in allowed_fields:
        if field in kwargs and kwargs[field] is not None:
            setattr(course, field, kwargs[field])

    db.session.commit()
    return course.to_dict()
