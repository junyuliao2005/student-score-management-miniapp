"""成绩路由：录入、修改、查询、删除"""
from flask import Blueprint, request, g
from app.middleware.jwt_middleware import jwt_required
from app.middleware.permission_middleware import permission_required
from app.services import score_service
from app.utils.response import success

score_bp = Blueprint('score', __name__)


@score_bp.route('/api/scores', methods=['POST'])
@jwt_required
@permission_required('score:create')
def create_score():
    """教师/管理员新增成绩"""
    data = request.get_json(force=True)
    result = score_service.create_score(
        payload=data,
        operator_id=g.current_user['user_id'],
        trace_id=getattr(request, 'trace_id', ''),
    )
    return success(result)


@score_bp.route('/api/scores/<int:score_id>', methods=['PUT'])
@jwt_required
@permission_required('score:update')
def update_score(score_id):
    """教师/管理员修改成绩"""
    data = request.get_json(force=True)
    result = score_service.update_score(
        score_id=score_id,
        payload=data,
        operator_id=g.current_user['user_id'],
        trace_id=getattr(request, 'trace_id', ''),
    )
    return success(result)


@score_bp.route('/api/scores', methods=['GET'])
@jwt_required
@permission_required('score:read:all')
def list_scores():
    """教师/管理员条件分页查询成绩"""
    filters = {
        'student_id': request.args.get('student_id'),
        'student_name': request.args.get('student_name'),
        'course_id': request.args.get('course_id'),
        'course_name': request.args.get('course_name'),
        'class_name': request.args.get('class_name'),
        'term': request.args.get('term'),
        'exam_batch': request.args.get('exam_batch'),
    }
    # 移除空值
    filters = {k: v for k, v in filters.items() if v}

    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)

    result = score_service.list_scores(filters, page, page_size)
    return success(result)


@score_bp.route('/api/scores/my', methods=['GET'])
@jwt_required
@permission_required('score:read:self')
def get_my_scores():
    """学生查询个人成绩"""
    student_id = g.current_user['user_id']
    filters = {
        'term': request.args.get('term'),
        'course_id': request.args.get('course_id'),
        'exam_batch': request.args.get('exam_batch'),
    }
    filters = {k: v for k, v in filters.items() if v}

    result = score_service.get_my_scores(student_id, filters)
    return success(result)


@score_bp.route('/api/scores/my/options', methods=['GET'])
@jwt_required
@permission_required('score:read:self')
def get_my_score_options():
    """学生查询自己实际有成绩的筛选选项。"""
    student_id = g.current_user['user_id']
    result = score_service.get_my_score_options(student_id)
    return success(result)


@score_bp.route('/api/scores/<int:score_id>', methods=['DELETE'])
@jwt_required
@permission_required('score:update')
def delete_score(score_id):
    """教师/管理员逻辑删除成绩"""
    result = score_service.soft_delete_score(
        score_id=score_id,
        operator_id=g.current_user['user_id'],
        trace_id=getattr(request, 'trace_id', ''),
    )
    return success(result)
