"""统计分析路由：总览、排名、等级评定"""
from flask import Blueprint, request, g
from app.middleware.jwt_middleware import jwt_required
from app.middleware.permission_middleware import permission_required
from app.services import stats_service
from app.services import audit_service
from app.utils.response import success

stats_bp = Blueprint('stats', __name__)


@stats_bp.route('/api/stats/overview', methods=['GET'])
@jwt_required
@permission_required('stats:read')
def overview():
    """班级或课程统计总览"""
    term = request.args.get('term')
    course_id = request.args.get('course_id')
    class_name = request.args.get('class_name')
    result = stats_service.get_overview(
        term=term, course_id=course_id, class_name=class_name, current_user=g.current_user,
    )
    return success(result)


@stats_bp.route('/api/stats/rankings', methods=['GET'])
@jwt_required
@permission_required('stats:read')
def rankings():
    """查询排名列表"""
    term = request.args.get('term')
    course_id = request.args.get('course_id')
    class_name = request.args.get('class_name')
    exam_batch = request.args.get('exam_batch')
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)

    result = stats_service.get_rankings(
        term=term, course_id=course_id, class_name=class_name, exam_batch=exam_batch,
        page=page, page_size=page_size, current_user=g.current_user,
    )
    return success(result)


@stats_bp.route('/api/stats/total-rankings', methods=['GET'])
@jwt_required
@permission_required('stats:read')
def total_rankings():
    """总分排名：按 term + exam_batch + class_name 实时聚合。"""
    term = request.args.get('term')
    exam_batch = request.args.get('exam_batch')
    class_name = request.args.get('class_name')
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)

    result = stats_service.get_total_rankings(
        term=term,
        exam_batch=exam_batch,
        class_name=class_name,
        page=page,
        page_size=page_size,
        current_user=g.current_user,
    )
    return success(result)


@stats_bp.route('/api/stats/honor-roll', methods=['GET'])
@jwt_required
@permission_required('stats:read')
def honor_roll():
    """荣誉榜：总分前 10、单科第一、优秀学生。"""
    term = request.args.get('term')
    exam_batch = request.args.get('exam_batch')
    class_name = request.args.get('class_name')
    result = stats_service.get_honor_roll(
        term=term, exam_batch=exam_batch, class_name=class_name, current_user=g.current_user,
    )
    return success(result)


@stats_bp.route('/api/stats/subject-rankings', methods=['GET'])
@jwt_required
@permission_required('stats:read')
def subject_rankings():
    """单科排名：按 term + exam_batch + course_id/course_name 查询。"""
    term = request.args.get('term')
    exam_batch = request.args.get('exam_batch')
    course_id = request.args.get('course_id') or request.args.get('course_name')
    class_name = request.args.get('class_name')
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)

    result = stats_service.get_subject_rankings(
        term=term,
        exam_batch=exam_batch,
        course_id=course_id,
        class_name=class_name,
        page=page,
        page_size=page_size,
        current_user=g.current_user,
    )
    return success(result)


@stats_bp.route('/api/stats/evaluate', methods=['POST'])
@jwt_required
@permission_required('stats:evaluate')
def evaluate():
    """手动触发等级评定、评语刷新和排名刷新"""
    data = request.get_json(force=True) if request.data else {}
    term = data.get('term')
    class_name = data.get('class_name')
    course_id = data.get('course_id')

    result = stats_service.evaluate_scores(
        term=term, class_name=class_name, course_id=course_id,
        operator_id=g.current_user['user_id'],
        trace_id=getattr(request, 'trace_id', ''),
        current_user=g.current_user,
    )

    audit_service.write(
        action='stats.evaluate',
        operator_id=g.current_user['user_id'],
        target_type='stats',
        target_id='all',
        detail={'term': term, 'class_name': class_name, 'course_id': course_id},
        trace_id=getattr(request, 'trace_id', ''),
    )

    return success(result)
