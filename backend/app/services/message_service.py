"""师生互动留言服务。"""
from datetime import datetime

from app.extensions import db
from app.models.course import Course
from app.models.message import Message
from app.models.role import Role
from app.models.score import Score
from app.models.teacher_binding import TeacherClassBinding
from app.models.user import User
from app.services import audit_service, teacher_scope_service
from app.utils.errors import BusinessError, ErrorCode
from app.utils.validators import validate_pagination


def list_messages(filters, current_user):
    page, page_size = validate_pagination({
        'page': filters.get('page', 1),
        'page_size': filters.get('page_size', 20),
    })

    roles = current_user.get('roles', [])
    user_id = current_user.get('user_id')

    query = Message.query.filter(Message.status == 1)
    if 'admin' not in roles:
        query = query.filter(db.or_(Message.sender_id == user_id, Message.receiver_id == user_id))

    box = filters.get('box')
    if box == 'received':
        query = query.filter(Message.receiver_id == user_id)
    elif box == 'sent':
        query = query.filter(Message.sender_id == user_id)

    if _to_bool(filters.get('unread_only')):
        query = query.filter(Message.is_read == 0)
        if 'admin' not in roles:
            query = query.filter(Message.receiver_id == user_id)

    if filters.get('student_id'):
        sid = filters['student_id']
        query = query.filter(db.or_(Message.sender_id == sid, Message.receiver_id == sid))
    if filters.get('teacher_id'):
        tid = filters['teacher_id']
        query = query.filter(db.or_(Message.sender_id == tid, Message.receiver_id == tid))
    if filters.get('course_id'):
        query = query.filter(Message.course_id == filters['course_id'])
    if filters.get('exam_batch'):
        query = query.filter(Message.exam_batch == filters['exam_batch'])

    total = query.count()
    items = query.order_by(Message.created_at.desc()) \
        .offset((page - 1) * page_size) \
        .limit(page_size) \
        .all()

    return {
        'list': [m.to_dict() for m in items],
        'page': page,
        'page_size': page_size,
        'total': total,
        'total_pages': (total + page_size - 1) // page_size,
    }


def create_message(payload, current_user, trace_id):
    sender_id = current_user.get('user_id')
    roles = current_user.get('roles', [])

    receiver_id = str(payload.get('receiver_id') or '').strip()
    title = str(payload.get('title') or '').strip()
    content = str(payload.get('content') or '').strip()
    course_id = _optional_str(payload.get('course_id'))
    exam_batch = _optional_str(payload.get('exam_batch'))
    related_score_id = payload.get('related_score_id')

    if not receiver_id:
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, '请选择接收人')
    if not title:
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, '请输入留言标题')
    if not content:
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, '请输入留言内容')

    sender = User.query.filter_by(user_id=sender_id, status=1).first()
    receiver = User.query.filter_by(user_id=receiver_id, status=1).first()
    if not sender:
        raise BusinessError(ErrorCode.LOGIN_REQUIRED, '当前用户不存在或已停用')
    if not receiver:
        raise BusinessError(ErrorCode.STUDENT_NOT_FOUND, '接收人不存在或已停用')

    _validate_sender_receiver(sender, receiver, roles)

    if 'teacher' in roles and 'admin' not in roles:
        teacher_scope_service.ensure_access(
            current_user, student_id=receiver_id, course_id=course_id,
        )

    if course_id and not Course.query.filter_by(course_id=course_id, status=1).first():
        raise BusinessError(ErrorCode.COURSE_NOT_FOUND, '课程不存在或已停用')

    if related_score_id:
        score = Score.query.filter_by(score_id=related_score_id, status=1).first()
        if not score:
            raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, '关联成绩不存在')

    message = Message(
        sender_id=sender_id,
        receiver_id=receiver_id,
        course_id=course_id,
        exam_batch=exam_batch,
        related_score_id=related_score_id,
        title=title[:100],
        content=content,
        is_read=0,
        status=1,
    )
    db.session.add(message)
    db.session.flush()

    audit_service.write(
        action='message.create',
        operator_id=sender_id,
        target_type='message',
        target_id=message.message_id,
        detail={'receiver_id': receiver_id, 'course_id': course_id, 'exam_batch': exam_batch},
        trace_id=trace_id,
    )

    db.session.commit()
    return message.to_dict()


def unread_count(current_user):
    user_id = current_user.get('user_id')
    count = Message.query.filter_by(receiver_id=user_id, status=1, is_read=0).count()
    return {'unread_count': count}


def mark_read(message_id, current_user, trace_id):
    message = Message.query.filter_by(message_id=message_id, status=1).first()
    if not message:
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, '留言不存在')

    roles = current_user.get('roles', [])
    user_id = current_user.get('user_id')
    if 'admin' not in roles and message.receiver_id != user_id:
        raise BusinessError(ErrorCode.PERMISSION_DENIED, '无权限标记该留言')

    if not message.is_read:
        message.is_read = 1
        message.read_at = datetime.now()

    audit_service.write(
        action='message.read',
        operator_id=user_id,
        target_type='message',
        target_id=message.message_id,
        detail=None,
        trace_id=trace_id,
    )
    db.session.commit()
    return message.to_dict()


def mark_all_read(current_user, trace_id):
    user_id = current_user.get('user_id')
    messages = Message.query.filter_by(receiver_id=user_id, status=1, is_read=0).all()
    now = datetime.now()
    for message in messages:
        message.is_read = 1
        message.read_at = now

    audit_service.write(
        action='message.read_all',
        operator_id=user_id,
        target_type='message',
        target_id='all',
        detail={'count': len(messages)},
        trace_id=trace_id,
    )
    db.session.commit()
    return {'updated_count': len(messages)}


def list_contacts(current_user):
    roles = current_user.get('roles', [])
    if 'student' in roles and 'teacher' not in roles and 'admin' not in roles:
        student_class = db.session.query(User.class_name).filter(User.user_id == current_user.get('user_id')).scalar()
        teacher_ids = db.session.query(TeacherClassBinding.teacher_id).filter(
            TeacherClassBinding.class_name == student_class,
            TeacherClassBinding.status == 1,
        )
        teachers = User.query.filter(
            User.status == 1,
            User.user_id.in_(teacher_ids),
            User.roles.any(Role.role_name == 'teacher'),
        ) \
            .order_by(User.user_id).all()
        admins = User.query.filter(User.status == 1, User.roles.any(Role.role_name == 'admin')) \
            .order_by(User.user_id).all()
        return {
            'students': [],
            'teachers': [_contact_dict(u) for u in teachers + admins],
        }

    students_query = User.query.filter(User.status == 1, User.roles.any(Role.role_name == 'student'))
    if 'teacher' in roles and 'admin' not in roles:
        class_names = teacher_scope_service.get_scope(current_user)['class_names']
        students_query = students_query.filter(User.class_name.in_(class_names))
    students = students_query.order_by(User.user_id).all()
    teachers = User.query.filter(User.status == 1, User.roles.any(Role.role_name == 'teacher')) \
        .order_by(User.user_id).all()
    return {
        'students': [_contact_dict(u) for u in students],
        'teachers': [_contact_dict(u) for u in teachers],
    }


def _validate_sender_receiver(sender, receiver, sender_roles):
    receiver_roles = receiver.get_role_names()
    if 'admin' in sender_roles:
        return
    if 'teacher' in sender_roles:
        if 'student' not in receiver_roles:
            raise BusinessError(ErrorCode.PERMISSION_DENIED, '教师只能给学生留言')
        return
    if 'student' in sender_roles:
        if 'teacher' not in receiver_roles and 'admin' not in receiver_roles:
            raise BusinessError(ErrorCode.PERMISSION_DENIED, '学生只能给教师或管理员留言')
        return
    raise BusinessError(ErrorCode.PERMISSION_DENIED, '无权限发送留言')


def _contact_dict(user):
    return {
        'user_id': user.user_id,
        'real_name': user.real_name,
        'class_name': user.class_name,
        'roles': user.get_role_names(),
    }


def _optional_str(value):
    text = str(value or '').strip()
    return text or None


def _to_bool(value):
    return str(value).lower() in ('1', 'true', 'yes')
