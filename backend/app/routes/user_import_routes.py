"""学生基础信息批量导入路由。"""
from flask import Blueprint, g, request

from app.middleware.jwt_middleware import jwt_required
from app.middleware.permission_middleware import role_required
from app.services import user_import_service
from app.utils.response import success

user_import_bp = Blueprint('user_import', __name__)


@user_import_bp.route('/api/users/import/preview', methods=['POST'])
@jwt_required
@role_required('admin')
def preview_user_import():
    """解析并校验 Excel 学生基础信息文件，不写入数据库。"""
    file_storage = request.files.get('file')
    result = user_import_service.preview_import(file_storage)
    return success(result)


@user_import_bp.route('/api/users/import/confirm', methods=['POST'])
@jwt_required
@role_required('admin')
def confirm_user_import():
    """确认导入 preview 中合法且不重复的学生账号。"""
    data = request.get_json(force=True)
    result = user_import_service.confirm_import(
        import_id=data.get('import_id'),
        operator_id=g.current_user['user_id'],
        trace_id=getattr(request, 'trace_id', ''),
    )
    return success(result)
