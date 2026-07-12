from flask import Blueprint, g, request

from app.middleware.jwt_middleware import jwt_required
from app.middleware.permission_middleware import permission_required
from app.services import analytics_service
from app.utils.response import success


analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route('/api/stats/trends', methods=['GET'])
@jwt_required
@permission_required('stats:read')
def trends():
    return success(analytics_service.get_trend(
        current_user=g.current_user,
        term=request.args.get('term'),
        class_name=request.args.get('class_name'),
        course_id=request.args.get('course_id'),
        student_id=request.args.get('student_id'),
    ))


@analytics_bp.route('/api/stats/my-trend', methods=['GET'])
@jwt_required
@permission_required('score:read:self')
def my_trend():
    return success(analytics_service.get_my_trend(
        student_id=g.current_user['user_id'],
        term=request.args.get('term'),
        course_id=request.args.get('course_id'),
    ))


@analytics_bp.route('/api/stats/distribution', methods=['GET'])
@jwt_required
@permission_required('stats:read')
def distribution():
    return success(analytics_service.get_distribution(
        current_user=g.current_user,
        term=request.args.get('term'),
        exam_batch=request.args.get('exam_batch'),
        class_name=request.args.get('class_name'),
        course_id=request.args.get('course_id'),
    ))


@analytics_bp.route('/api/stats/progress-rankings', methods=['GET'])
@jwt_required
@permission_required('stats:read')
def progress_rankings():
    return success(analytics_service.get_progress_rankings(
        current_user=g.current_user,
        term=request.args.get('term'),
        baseline_batch=request.args.get('baseline_batch'),
        current_batch=request.args.get('current_batch'),
        class_name=request.args.get('class_name'),
        page=request.args.get('page', 1, type=int),
        page_size=request.args.get('page_size', 20, type=int),
    ))


@analytics_bp.route('/api/stats/bias-analysis', methods=['GET'])
@jwt_required
@permission_required('stats:read')
def bias_analysis():
    return success(analytics_service.get_bias_analysis(
        current_user=g.current_user,
        term=request.args.get('term'),
        exam_batch=request.args.get('exam_batch'),
        class_name=request.args.get('class_name'),
        page=request.args.get('page', 1, type=int),
        page_size=request.args.get('page_size', 20, type=int),
    ))
