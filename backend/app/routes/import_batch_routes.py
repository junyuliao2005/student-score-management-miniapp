from flask import Blueprint, g, request

from app.middleware.jwt_middleware import jwt_required
from app.middleware.permission_middleware import role_required
from app.services import import_batch_service
from app.utils.response import success


import_batch_bp = Blueprint('import_batch', __name__)


@import_batch_bp.route('/api/import-batches', methods=['GET'])
@jwt_required
@role_required('admin')
def list_import_batches():
    return success(import_batch_service.list_batches(
        page=request.args.get('page', 1, type=int),
        page_size=request.args.get('page_size', 20, type=int),
        import_type=request.args.get('import_type'),
        status=request.args.get('status'),
        operator_user_id=request.args.get('operator_user_id'),
    ))


@import_batch_bp.route('/api/import-batches/<import_batch_id>', methods=['GET'])
@jwt_required
@role_required('admin')
def get_import_batch(import_batch_id):
    return success(import_batch_service.get_batch(import_batch_id))


@import_batch_bp.route('/api/import-batches/<import_batch_id>/rollback', methods=['POST'])
@jwt_required
@role_required('admin')
def rollback_import_batch(import_batch_id):
    return success(import_batch_service.rollback_batch(
        import_batch_id=import_batch_id,
        operator_user_id=g.current_user['user_id'],
        trace_id=getattr(request, 'trace_id', ''),
    ))
