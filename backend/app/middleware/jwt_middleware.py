"""JWT 认证中间件"""
import jwt
import logging
from functools import wraps
from flask import request, g, current_app
from app.utils.errors import BusinessError, ErrorCode

logger = logging.getLogger(__name__)


def _extract_token():
    """从请求头提取 JWT token"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header:
        return None
    parts = auth_header.split()
    if len(parts) == 2 and parts[0].lower() == 'bearer':
        return parts[1]
    return None


def _decode_token(token):
    """解码并验证 JWT token"""
    try:
        payload = jwt.decode(
            token,
            current_app.config['JWT_SECRET_KEY'],
            algorithms=['HS256']
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise BusinessError(ErrorCode.TOKEN_EXPIRED, 'TOKEN_EXPIRED')
    except jwt.InvalidTokenError:
        raise BusinessError(ErrorCode.TOKEN_INVALID, 'TOKEN_INVALID')


def jwt_required(f):
    """JWT 认证装饰器，要求请求必须携带有效 token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _extract_token()
        if not token:
            raise BusinessError(ErrorCode.LOGIN_REQUIRED, 'LOGIN_REQUIRED')
        payload = _decode_token(token)
        g.current_user = payload
        return f(*args, **kwargs)
    return decorated


def jwt_optional(f):
    """JWT 可选装饰器，有 token 则解析，没有则跳过"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _extract_token()
        if token:
            try:
                payload = _decode_token(token)
                g.current_user = payload
            except BusinessError:
                g.current_user = None
        else:
            g.current_user = None
        return f(*args, **kwargs)
    return decorated
