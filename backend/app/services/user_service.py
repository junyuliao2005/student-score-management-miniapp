"""用户管理服务"""
from app.extensions import db
from app.models.user import User
from app.models.role import Role, UserRole
from app.utils.hash_util import hash_password
from app.utils.errors import BusinessError, ErrorCode
from app.utils.validators import validate_pagination


def list_users(page=1, page_size=20, keyword=None, role_name=None):
    """分页查询用户"""
    page, page_size = validate_pagination({'page': page, 'page_size': page_size})

    query = User.query
    if keyword:
        like = f'%{keyword}%'
        query = query.filter(
            db.or_(User.username.like(like), User.real_name.like(like), User.user_id.like(like))
        )
    if role_name:
        query = query.filter(User.roles.any(Role.role_name == role_name))

    total = query.count()
    items = query.order_by(User.created_at.desc()) \
        .offset((page - 1) * page_size) \
        .limit(page_size) \
        .all()

    return {
        'list': [u.to_dict() for u in items],
        'page': page,
        'page_size': page_size,
        'total': total,
    }


def list_class_names():
    """查询启用用户关联的班级名称列表"""
    rows = db.session.query(User.class_name) \
        .filter(User.status == 1) \
        .filter(User.class_name.isnot(None)) \
        .filter(db.func.trim(User.class_name) != '') \
        .distinct() \
        .order_by(User.class_name.asc()) \
        .all()

    return {
        'classes': [row[0] for row in rows],
    }


def create_user(user_id, username, password, real_name, class_name=None, role_name='student'):
    """新增用户"""
    # 唯一性检查
    if User.query.filter_by(user_id=user_id).first():
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, f'用户ID {user_id} 已存在')
    if User.query.filter_by(username=username).first():
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, f'用户名 {username} 已存在')

    user = User(
        user_id=user_id,
        username=username,
        password_hash=hash_password(password),
        real_name=real_name,
        class_name=class_name,
        status=1,
    )
    db.session.add(user)
    db.session.flush()

    # 分配角色
    role = Role.query.filter_by(role_name=role_name).first()
    if role:
        db.session.add(UserRole(user_id=user_id, role_id=role.role_id))

    db.session.commit()
    return user.to_dict()


def update_user(user_id, **kwargs):
    """修改用户信息"""
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        raise BusinessError(ErrorCode.STUDENT_NOT_FOUND, '用户不存在')

    allowed_fields = ['real_name', 'class_name', 'status']
    for field in allowed_fields:
        if field in kwargs:
            setattr(user, field, kwargs[field])

    # 如果传了密码，更新密码
    if 'password' in kwargs and kwargs['password']:
        user.password_hash = hash_password(kwargs['password'])

    # 如果传了角色，更新角色
    if 'role_name' in kwargs and kwargs['role_name']:
        UserRole.query.filter_by(user_id=user_id).delete()
        role = Role.query.filter_by(role_name=kwargs['role_name']).first()
        if role:
            db.session.add(UserRole(user_id=user_id, role_id=role.role_id))

    db.session.commit()
    return user.to_dict()


def get_user_by_id(user_id):
    """根据 ID 查询用户"""
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return None
    return user.to_dict()
