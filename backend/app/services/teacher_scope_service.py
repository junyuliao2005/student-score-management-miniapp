"""Explicit teacher class/course scope management and authorization."""
from app.extensions import db
from sqlalchemy import false
from app.models.course import Course
from app.models.role import Role
from app.models.score import Score
from app.models.teacher_binding import TeacherClassBinding, TeacherCourseBinding
from app.models.user import User
from app.services import audit_service
from app.utils.errors import BusinessError, ErrorCode


def is_admin(current_user):
    return 'admin' in _roles(current_user)


def is_teacher(current_user):
    return 'teacher' in _roles(current_user)


def get_scope(current_user):
    if is_admin(current_user):
        return {'unrestricted': True, 'class_names': [], 'course_ids': []}
    if not is_teacher(current_user):
        raise BusinessError(ErrorCode.PERMISSION_DENIED, '当前账号无教师数据范围')
    teacher_id = str((current_user or {}).get('user_id') or '')
    classes = db.session.query(TeacherClassBinding.class_name).filter(
        TeacherClassBinding.teacher_id == teacher_id,
        TeacherClassBinding.status == 1,
    ).order_by(TeacherClassBinding.class_name).all()
    courses = db.session.query(TeacherCourseBinding.course_id).filter(
        TeacherCourseBinding.teacher_id == teacher_id,
        TeacherCourseBinding.status == 1,
    ).order_by(TeacherCourseBinding.course_id).all()
    return {
        'unrestricted': False,
        'class_names': [row.class_name for row in classes],
        'course_ids': [row.course_id for row in courses],
    }


def ensure_access(current_user, student_id=None, course_id=None, class_name=None):
    """Require a teacher to own both the student class and course scope."""
    if is_admin(current_user):
        return
    if not is_teacher(current_user):
        raise BusinessError(ErrorCode.PERMISSION_DENIED, '无权访问教师数据')

    resolved_class = str(class_name or '').strip()
    if student_id:
        student = db.session.query(User.class_name).filter(
            User.user_id == student_id,
            User.status == 1,
        ).first()
        if not student:
            raise BusinessError(ErrorCode.STUDENT_NOT_FOUND, '学生不存在或状态异常')
        resolved_class = str(student.class_name or '').strip()

    scope = get_scope(current_user)
    if resolved_class and resolved_class not in scope['class_names']:
        raise BusinessError(ErrorCode.PERMISSION_DENIED, '该班级不在当前教师授权范围内')
    if not resolved_class and (student_id or class_name is not None):
        raise BusinessError(ErrorCode.PERMISSION_DENIED, '学生班级为空，无法确认教师数据范围')
    if course_id and str(course_id).strip() not in scope['course_ids']:
        raise BusinessError(ErrorCode.PERMISSION_DENIED, '该课程不在当前教师授权范围内')


def apply_score_scope(query, current_user):
    """Apply scope without loading User.roles/permissions relationships."""
    if is_admin(current_user):
        return query
    if not is_teacher(current_user):
        return query.filter(false())
    teacher_id = str((current_user or {}).get('user_id') or '')
    class_names = db.session.query(TeacherClassBinding.class_name).filter(
        TeacherClassBinding.teacher_id == teacher_id,
        TeacherClassBinding.status == 1,
    )
    course_ids = db.session.query(TeacherCourseBinding.course_id).filter(
        TeacherCourseBinding.teacher_id == teacher_id,
        TeacherCourseBinding.status == 1,
    )
    student_ids = db.session.query(User.user_id).filter(
        User.status == 1,
        User.class_name.in_(class_names),
    )
    return query.filter(Score.student_id.in_(student_ids), Score.course_id.in_(course_ids))


def list_bindings(teacher_id=None):
    teacher_query = User.query.filter(User.status == 1, User.roles.any(Role.role_name == 'teacher'))
    if teacher_id:
        teacher_query = teacher_query.filter(User.user_id == teacher_id)
    teachers = teacher_query.order_by(User.user_id).all()
    result = []
    for teacher in teachers:
        class_rows = TeacherClassBinding.query.filter_by(teacher_id=teacher.user_id, status=1) \
            .order_by(TeacherClassBinding.class_name).all()
        course_rows = db.session.query(TeacherCourseBinding.course_id, Course.course_name).join(
            Course, TeacherCourseBinding.course_id == Course.course_id
        ).filter(
            TeacherCourseBinding.teacher_id == teacher.user_id,
            TeacherCourseBinding.status == 1,
        ).order_by(TeacherCourseBinding.course_id).all()
        result.append({
            'teacher_id': teacher.user_id,
            'teacher_name': teacher.real_name,
            'class_names': [row.class_name for row in class_rows],
            'courses': [
                {'course_id': row.course_id, 'course_name': row.course_name}
                for row in course_rows
            ],
        })
    return {'list': result, 'total': len(result)}


def replace_bindings(teacher_id, payload, operator_id, trace_id=''):
    teacher = User.query.filter(
        User.user_id == teacher_id,
        User.status == 1,
        User.roles.any(Role.role_name == 'teacher'),
    ).first()
    if not teacher:
        raise BusinessError(ErrorCode.PERMISSION_DENIED, '教师不存在或未启用')

    class_names = _normalized_values((payload or {}).get('class_names'), 30)
    course_ids = _normalized_values((payload or {}).get('course_ids'), 20)
    if class_names:
        known_classes = {
            row.class_name for row in db.session.query(User.class_name).filter(
                User.status == 1,
                User.class_name.in_(class_names),
            ).distinct().all()
        }
        unknown = sorted(set(class_names) - known_classes)
        if unknown:
            raise BusinessError(ErrorCode.PERMISSION_DENIED, f'班级不存在: {", ".join(unknown)}')
    if course_ids:
        known_courses = {
            row.course_id for row in db.session.query(Course.course_id).filter(
                Course.status == 1,
                Course.course_id.in_(course_ids),
            ).all()
        }
        unknown = sorted(set(course_ids) - known_courses)
        if unknown:
            raise BusinessError(ErrorCode.COURSE_NOT_FOUND, f'课程不存在或已停用: {", ".join(unknown)}')

    try:
        _replace_class_rows(teacher_id, class_names, operator_id)
        _replace_course_rows(teacher_id, course_ids, operator_id)
        audit_service.write(
            action='teacher_scope.replace',
            operator_id=operator_id,
            target_type='teacher',
            target_id=teacher_id,
            detail={'class_names': class_names, 'course_ids': course_ids},
            trace_id=trace_id,
        )
        db.session.commit()
    except BusinessError:
        db.session.rollback()
        raise
    except Exception as exc:
        db.session.rollback()
        raise BusinessError(ErrorCode.DB_TRANSACTION_FAILED, '教师绑定保存失败') from exc
    return list_bindings(teacher_id)['list'][0]


def _replace_class_rows(teacher_id, values, operator_id):
    existing = {row.class_name: row for row in TeacherClassBinding.query.filter_by(teacher_id=teacher_id).all()}
    selected = set(values)
    for value, row in existing.items():
        row.status = 1 if value in selected else 0
    for value in selected - set(existing):
        db.session.add(TeacherClassBinding(
            teacher_id=teacher_id, class_name=value, status=1, created_by=operator_id,
        ))


def _replace_course_rows(teacher_id, values, operator_id):
    existing = {row.course_id: row for row in TeacherCourseBinding.query.filter_by(teacher_id=teacher_id).all()}
    selected = set(values)
    for value, row in existing.items():
        row.status = 1 if value in selected else 0
    for value in selected - set(existing):
        db.session.add(TeacherCourseBinding(
            teacher_id=teacher_id, course_id=value, status=1, created_by=operator_id,
        ))


def _normalized_values(values, max_length):
    if values is None:
        return []
    if not isinstance(values, list):
        raise BusinessError(ErrorCode.PERMISSION_DENIED, '绑定字段必须是数组')
    result = []
    seen = set()
    for item in values:
        value = str(item or '').strip()
        if not value or value in seen:
            continue
        if len(value) > max_length:
            raise BusinessError(ErrorCode.PERMISSION_DENIED, '绑定值长度不合法')
        seen.add(value)
        result.append(value)
    return result


def _roles(current_user):
    values = (current_user or {}).get('roles') or []
    return values if isinstance(values, list) else []
