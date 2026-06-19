"""认证路由：登录、用户信息"""
from flask import Blueprint, request, g
from app.extensions import db
from app.middleware.jwt_middleware import jwt_required
from app.services import auth_manager
from app.services import audit_service
from app.utils.response import success, fail
from app.utils.validators import require_fields
from app.utils.errors import BusinessError

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json(force=True)
    require_fields(data, ['username', 'password'])

    try:
        result = auth_manager.login(data['username'], data['password'])
    except BusinessError as exc:
        audit_service.write(
            action='auth.login_failed',
            operator_id='anonymous',
            target_type='user',
            target_id=str(data.get('username') or ''),
            detail={'username': data.get('username'), 'reason': exc.message},
            trace_id=getattr(request, 'trace_id', ''),
            result_code=exc.code,
        )
        db.session.commit()
        raise

    # 审计日志
    audit_service.write(
        action='auth.login',
        operator_id=result['user']['user_id'],
        target_type='user',
        target_id=result['user']['user_id'],
        detail={'username': data['username']},
        trace_id=getattr(request, 'trace_id', ''),
    )
    db.session.commit()

    return success(result)


@auth_bp.route('/api/auth/profile', methods=['GET'])
@jwt_required
def profile():
    """获取当前用户信息"""
    user_id = g.current_user['user_id']
    result = auth_manager.get_profile(user_id)
    return success(result)
