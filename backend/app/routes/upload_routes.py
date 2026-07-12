"""CloudBase temporary-file consumption routes."""
from flask import Blueprint, g, request

from app.middleware.jwt_middleware import jwt_required
from app.middleware.permission_middleware import permission_required, role_required
from app.services import cloud_upload_service, ocr_service, score_import_service, user_import_service
from app.utils.response import success
from app.utils.upload_security import check_upload_rate_limit

upload_bp = Blueprint('upload', __name__)


@upload_bp.route('/api/uploads/cloud/scores/import/preview', methods=['POST'])
@jwt_required
@permission_required('score:create')
def cloud_score_import_preview():
    check_upload_rate_limit(g.current_user['user_id'], 'cloud_score_import', limit=10, window_seconds=60)
    payload = request.get_json(force=True) if request.data else {}
    file_storage = cloud_upload_service.fetch_as_file_storage(payload, max_size_mb=10)
    return success(score_import_service.preview_import(file_storage, g.current_user))


@upload_bp.route('/api/uploads/cloud/users/import/preview', methods=['POST'])
@jwt_required
@role_required('admin')
def cloud_user_import_preview():
    check_upload_rate_limit(g.current_user['user_id'], 'cloud_user_import', limit=10, window_seconds=60)
    payload = request.get_json(force=True) if request.data else {}
    file_storage = cloud_upload_service.fetch_as_file_storage(payload, max_size_mb=10)
    return success(user_import_service.preview_import(file_storage, g.current_user['user_id']))


@upload_bp.route('/api/uploads/cloud/exam-paper/ocr-preview', methods=['POST'])
@jwt_required
@permission_required('ai:exam_analyze')
def cloud_exam_ocr_preview():
    check_upload_rate_limit(g.current_user['user_id'], 'cloud_exam_ocr', limit=6, window_seconds=60)
    payload = request.get_json(force=True) if request.data else {}
    file_storage = cloud_upload_service.fetch_as_file_storage(payload, max_size_mb=10)
    return success(ocr_service.preview_image(
        image_file=file_storage,
        operator_id=g.current_user['user_id'],
        trace_id=getattr(request, 'trace_id', ''),
    ))
