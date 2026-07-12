from flask import Blueprint, g, request

from app.middleware.jwt_middleware import jwt_required
from app.middleware.permission_middleware import permission_required, role_required
from app.services import report_service
from app.utils.response import success


report_bp = Blueprint('report', __name__)


@report_bp.route('/api/reports/scores/export', methods=['GET'])
@jwt_required
@permission_required('score:read:all')
def export_scores():
    filters = {
        key: request.args.get(key)
        for key in ('term', 'exam_batch', 'class_name', 'course_id', 'student_id')
        if request.args.get(key)
    }
    return success(report_service.export_scores_xlsx(g.current_user, filters))


@report_bp.route('/api/reports/students/<student_id>/scores.pdf', methods=['GET'])
@jwt_required
def student_scores_pdf(student_id):
    return success(report_service.student_score_pdf(
        current_user=g.current_user,
        student_id=student_id,
        term=request.args.get('term'),
        exam_batch=request.args.get('exam_batch'),
    ))
