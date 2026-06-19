"""通用选项接口。"""
from flask import Blueprint, g, request

from app.middleware.jwt_middleware import jwt_required
from app.services import options_service
from app.utils.response import success

options_bp = Blueprint('options', __name__)


@options_bp.route('/api/options', methods=['GET'])
@jwt_required
def get_options():
    """按当前用户角色返回输入框辅助选项。"""
    option_type = request.args.get('type')
    result = options_service.get_options(option_type, g.current_user)
    return success(result)
