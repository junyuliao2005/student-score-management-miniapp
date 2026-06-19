"""RBAC 权限校验中间件"""
from functools import wraps
from flask import g
from app.utils.errors import BusinessError, ErrorCode
from app.middleware.jwt_middleware import jwt_required


def permission_required(permission_code):
    """权限校验装饰器，必须配合 jwt_required 使用。

    用法:
        @app.route('/api/xxx')
        @jwt_required
        @permission_required('user:manage')
        def xxx():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            current_user = getattr(g, 'current_user', None)
            if not current_user:
                raise BusinessError(ErrorCode.LOGIN_REQUIRED, 'LOGIN_REQUIRED')

            user_permissions = current_user.get('permissions', [])
            if permission_code not in user_permissions:
                raise BusinessError(ErrorCode.PERMISSION_DENIED, 'PERMISSION_DENIED')

            return f(*args, **kwargs)
        return decorated
    return decorator


def role_required(*role_names):
    """角色校验装饰器，要求用户拥有指定角色之一。

    用法:
        @app.route('/api/xxx')
        @jwt_required
        @role_required('admin', 'teacher')
        def xxx():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            current_user = getattr(g, 'current_user', None)
            if not current_user:
                raise BusinessError(ErrorCode.LOGIN_REQUIRED, 'LOGIN_REQUIRED')

            user_roles = current_user.get('roles', [])
            if not any(r in user_roles for r in role_names):
                raise BusinessError(ErrorCode.PERMISSION_DENIED, 'PERMISSION_DENIED')

            return f(*args, **kwargs)
        return decorated
    return decorator
