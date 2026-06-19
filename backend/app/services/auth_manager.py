"""认证服务：登录、JWT 签发、用户信息"""
import jwt
import logging
from datetime import datetime, timedelta
from flask import current_app
from app.extensions import db
from app.models.user import User
from app.utils.hash_util import verify_password
from app.utils.errors import BusinessError, ErrorCode

logger = logging.getLogger(__name__)


def login(username, password):
    """账号密码登录，返回 token 和用户信息"""
    user = User.query.filter_by(username=username).first()
    if not user:
        raise BusinessError(ErrorCode.LOGIN_REQUIRED, '用户名或密码错误')

    if user.status != 1:
        raise BusinessError(ErrorCode.PERMISSION_DENIED, '账号已被禁用')

    if not verify_password(password, user.password_hash):
        raise BusinessError(ErrorCode.LOGIN_REQUIRED, '用户名或密码错误')

    # 生成 JWT
    token = _generate_token(user)

    return {
        'token': token,
        'user': {
            'user_id': user.user_id,
            'real_name': user.real_name,
            'class_name': user.class_name,
        },
        'roles': user.get_role_names(),
        'permissions': user.get_permissions(),
    }


def get_profile(user_id):
    """获取用户详细信息"""
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        raise BusinessError(ErrorCode.STUDENT_NOT_FOUND, '用户不存在')
    return {
        'user_id': user.user_id,
        'username': user.username,
        'real_name': user.real_name,
        'class_name': user.class_name,
        'status': user.status,
        'roles': user.get_role_names(),
        'permissions': user.get_permissions(),
        'created_at': user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else None,
    }


def _generate_token(user):
    """生成 JWT token"""
    expire_hours = current_app.config.get('JWT_EXPIRE_HOURS', 2)
    payload = {
        'sub': user.user_id,
        'user_id': user.user_id,
        'username': user.username,
        'real_name': user.real_name,
        'roles': user.get_role_names(),
        'permissions': user.get_permissions(),
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(hours=expire_hours),
    }
    token = jwt.encode(
        payload,
        current_app.config['JWT_SECRET_KEY'],
        algorithm='HS256'
    )
    return token
