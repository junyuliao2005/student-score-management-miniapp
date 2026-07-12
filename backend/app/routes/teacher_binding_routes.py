from flask import Blueprint, g, request

from app.middleware.jwt_middleware import jwt_required
from app.middleware.permission_middleware import role_required
from app.services import teacher_scope_service
from app.utils.response import success


teacher_binding_bp = Blueprint('teacher_binding', __name__)


@teacher_binding_bp.route('/api/admin/teacher-bindings', methods=['GET'])
@jwt_required
@role_required('admin')
def list_teacher_bindings():
    return success(teacher_scope_service.list_bindings(request.args.get('teacher_id')))


@teacher_binding_bp.route('/api/admin/teacher-bindings/<teacher_id>', methods=['PUT'])
@jwt_required
@role_required('admin')
def replace_teacher_bindings(teacher_id):
    payload = request.get_json(force=True) if request.data else {}
    return success(teacher_scope_service.replace_bindings(
        teacher_id=teacher_id,
        payload=payload,
        operator_id=g.current_user['user_id'],
        trace_id=getattr(request, 'trace_id', ''),
    ))
