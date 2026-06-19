"""管理员路由：角色查询、审计日志"""
from flask import Blueprint, request, g
from app.middleware.jwt_middleware import jwt_required
from app.middleware.permission_middleware import permission_required
from app.models.role import Role
from app.models.audit_log import AuditLog
from app.utils.response import success
from app.utils.validators import validate_pagination

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/api/admin/roles', methods=['GET'])
@jwt_required
@permission_required('role:manage')
def list_roles():
    """查询所有角色及其权限"""
    roles = Role.query.all()
    result = []
    for r in roles:
        result.append({
            'role_id': r.role_id,
            'role_name': r.role_name,
            'description': r.description,
            'permissions': [p.permission_code for p in r.permissions],
        })
    return success(result)


@admin_bp.route('/api/admin/logs', methods=['GET'])
@jwt_required
@permission_required('log:read')
def list_logs():
    """分页查询审计日志"""
    page, page_size = validate_pagination(request.args.to_dict())

    query = AuditLog.query

    # 可选过滤条件
    operator_id = request.args.get('operator_id')
    action = request.args.get('action')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if operator_id:
        query = query.filter_by(operator_id=operator_id)
    if action:
        query = query.filter(AuditLog.action.like(f'%{action}%'))
    if start_date:
        query = query.filter(AuditLog.created_at >= start_date)
    if end_date:
        query = query.filter(AuditLog.created_at <= end_date + ' 23:59:59')

    total = query.count()
    items = query.order_by(AuditLog.created_at.desc()) \
        .offset((page - 1) * page_size) \
        .limit(page_size) \
        .all()

    return success({
        'list': [log.to_dict() for log in items],
        'page': page,
        'page_size': page_size,
        'total': total,
    })
