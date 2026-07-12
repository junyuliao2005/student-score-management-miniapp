"""成绩批量导入路由。"""
from flask import Blueprint, g, request

from app.middleware.jwt_middleware import jwt_required
from app.middleware.permission_middleware import permission_required
from app.services import score_import_service
from app.utils.response import success
from app.utils.upload_security import check_upload_rate_limit

score_import_bp = Blueprint('score_import', __name__)


@score_import_bp.route('/api/scores/import/preview', methods=['POST'])
@jwt_required
@permission_required('score:create')
def preview_score_import():
    """解析并校验 Excel 成绩文件，不写入数据库。"""
    check_upload_rate_limit(g.current_user['user_id'], 'score_import_preview', limit=10, window_seconds=60)
    file_storage = request.files.get('file')
    result = score_import_service.preview_import(file_storage, g.current_user)
    return success(result)


@score_import_bp.route('/api/scores/import/confirm', methods=['POST'])
@jwt_required
@permission_required('score:create')
def confirm_score_import():
    """确认导入 preview 中合法且不重复的成绩。"""
    check_upload_rate_limit(g.current_user['user_id'], 'score_import_confirm', limit=10, window_seconds=60)
    data = request.get_json(force=True)
    result = score_import_service.confirm_import(
        import_id=data.get('import_id'),
        operator_id=g.current_user['user_id'],
        trace_id=getattr(request, 'trace_id', ''),
        current_user=g.current_user,
    )
    return success(result)
