"""成绩发布、家长绑定与家长端接口。"""
from flask import Blueprint, g, request

from app.middleware.jwt_middleware import jwt_required
from app.middleware.permission_middleware import role_required
from app.services import exam_publish_service
from app.utils.response import success

exam_publish_bp = Blueprint('exam_publish', __name__)


@exam_publish_bp.route('/api/exam-publish', methods=['GET'])
@jwt_required
@role_required('teacher', 'admin')
def list_publish_settings():
    filters = {
        'term': request.args.get('term'),
        'exam_batch': request.args.get('exam_batch'),
        'grade_name': request.args.get('grade_name'),
        'class_name': request.args.get('class_name'),
        'status': request.args.get('status'),
    }
    filters = {k: v for k, v in filters.items() if v}
    result = exam_publish_service.list_publish_settings(
        filters,
        page=request.args.get('page', 1, type=int),
        page_size=request.args.get('page_size', 20, type=int),
        current_user=g.current_user,
    )
    return success(result)


@exam_publish_bp.route('/api/exam-publish', methods=['POST'])
@jwt_required
@role_required('teacher', 'admin')
def create_publish_setting():
    data = request.get_json(force=True) if request.data else {}
    result = exam_publish_service.create_publish_setting(data, g.current_user, getattr(request, 'trace_id', ''))
    return success(result)


@exam_publish_bp.route('/api/exam-publish/<int:setting_id>', methods=['PUT'])
@jwt_required
@role_required('teacher', 'admin')
def update_publish_setting(setting_id):
    data = request.get_json(force=True) if request.data else {}
    result = exam_publish_service.update_publish_setting(setting_id, data, g.current_user, getattr(request, 'trace_id', ''))
    return success(result)


@exam_publish_bp.route('/api/exam-publish/<int:setting_id>', methods=['DELETE'])
@jwt_required
@role_required('teacher', 'admin')
def delete_publish_setting(setting_id):
    result = exam_publish_service.delete_publish_setting(setting_id, g.current_user, getattr(request, 'trace_id', ''))
    return success(result)


@exam_publish_bp.route('/api/exam-publish/<int:setting_id>/publish', methods=['POST'])
@jwt_required
@role_required('teacher', 'admin')
def publish_setting(setting_id):
    result = exam_publish_service.publish_setting(setting_id, g.current_user, getattr(request, 'trace_id', ''))
    return success(result)


@exam_publish_bp.route('/api/exam-publish/<int:setting_id>/withdraw', methods=['POST'])
@jwt_required
@role_required('teacher', 'admin')
def withdraw_setting(setting_id):
    result = exam_publish_service.withdraw_setting(setting_id, g.current_user, getattr(request, 'trace_id', ''))
    return success(result)


@exam_publish_bp.route('/api/exam-publish/<int:setting_id>/confirmations', methods=['GET'])
@jwt_required
@role_required('teacher', 'admin')
def list_confirmations(setting_id):
    filters = {
        'status': request.args.get('status'),
        'class_name': request.args.get('class_name'),
    }
    filters = {k: v for k, v in filters.items() if v}
    result = exam_publish_service.list_confirmations(setting_id, g.current_user, filters)
    return success(result)


@exam_publish_bp.route('/api/exam-publish/<int:setting_id>/confirmations/export', methods=['GET'])
@jwt_required
@role_required('teacher', 'admin')
def export_confirmations(setting_id):
    return success(exam_publish_service.export_confirmations(setting_id, g.current_user))


@exam_publish_bp.route('/api/parent-bindings', methods=['GET'])
@jwt_required
@role_required('teacher', 'admin')
def list_parent_bindings():
    filters = {
        'parent_user_id': request.args.get('parent_user_id'),
        'student_user_id': request.args.get('student_user_id'),
        'status': request.args.get('status'),
    }
    filters = {k: v for k, v in filters.items() if v is not None and v != ''}
    result = exam_publish_service.list_bindings(filters, g.current_user)
    return success(result)


@exam_publish_bp.route('/api/parent-bindings', methods=['POST'])
@jwt_required
@role_required('admin')
def create_parent_binding():
    data = request.get_json(force=True) if request.data else {}
    result = exam_publish_service.create_binding(data, g.current_user, getattr(request, 'trace_id', ''))
    return success(result)


@exam_publish_bp.route('/api/parent-bindings/<int:binding_id>', methods=['DELETE'])
@jwt_required
@role_required('admin')
def disable_parent_binding(binding_id):
    result = exam_publish_service.disable_binding(binding_id, g.current_user, getattr(request, 'trace_id', ''))
    return success(result)


@exam_publish_bp.route('/api/parents/my-children', methods=['GET'])
@jwt_required
@role_required('parent')
def my_children():
    result = exam_publish_service.my_children(g.current_user)
    return success(result)


@exam_publish_bp.route('/api/parents/children/<student_id>/published-scores', methods=['GET'])
@jwt_required
@role_required('parent')
def parent_published_scores(student_id):
    result = exam_publish_service.parent_published_scores(student_id, g.current_user)
    return success(result)


@exam_publish_bp.route('/api/parents/confirmations/<int:publish_id>/confirm', methods=['POST'])
@jwt_required
@role_required('parent')
def parent_confirm_score(publish_id):
    data = request.get_json(force=True) if request.data else {}
    result = exam_publish_service.confirm_score(publish_id, data, g.current_user, getattr(request, 'trace_id', ''))
    return success(result)
