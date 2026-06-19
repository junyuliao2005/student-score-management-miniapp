"""预警路由：查询预警名单、刷新预警"""
from flask import Blueprint, request, g
from app.middleware.jwt_middleware import jwt_required
from app.middleware.permission_middleware import permission_required
from app.services import warning_calculator
from app.services import audit_service
from app.utils.response import success

warning_bp = Blueprint('warning', __name__)


@warning_bp.route('/api/warnings', methods=['GET'])
@jwt_required
@permission_required('warning:read')
def list_warnings():
    """查询预警名单"""
    filters = {
        'term': request.args.get('term'),
        'class_name': request.args.get('class_name'),
        'warning_type': request.args.get('warning_type'),
    }
    filters = {k: v for k, v in filters.items() if v}

    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)

    result = warning_calculator.get_warning_list(filters, page, page_size)
    return success(result)


@warning_bp.route('/api/warnings/refresh', methods=['POST'])
@jwt_required
@permission_required('warning:refresh')
def refresh_warnings():
    """刷新预警"""
    data = request.get_json(force=True) if request.data else {}
    term = data.get('term')
    class_name = data.get('class_name')

    result = warning_calculator.refresh_warnings(
        term=term, class_name=class_name,
        operator_id=g.current_user['user_id'],
        trace_id=getattr(request, 'trace_id', ''),
    )

    audit_service.write(
        action='warning.refresh',
        operator_id=g.current_user['user_id'],
        target_type='warning',
        target_id='all',
        detail={'term': term, 'class_name': class_name},
        trace_id=getattr(request, 'trace_id', ''),
    )

    return success(result)
