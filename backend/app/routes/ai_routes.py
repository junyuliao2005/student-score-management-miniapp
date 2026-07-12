"""AI 分析路由"""
from flask import Blueprint, request, g
from app.middleware.jwt_middleware import jwt_required
from app.middleware.permission_middleware import permission_required
from app.extensions import db
from app.services import ai_service
from app.services import exam_analyzer
from app.services import vision_exam_analyzer
from app.services import ocr_service
from app.services import audit_service
from app.services import teacher_scope_service
from app.utils.response import success
from app.utils.errors import BusinessError, ErrorCode
from app.utils.upload_security import check_upload_rate_limit

ai_bp = Blueprint('ai', __name__)


def _require_any_permission(*perms):
    """检查用户是否拥有任意一个指定权限"""
    from functools import wraps
    def decorator(f):
        @wraps(f)
        @jwt_required
        def wrapper(*args, **kwargs):
            user_perms = g.current_user.get('permissions', [])
            if not any(p in user_perms for p in perms):
                raise BusinessError(ErrorCode.PERMISSION_DENIED, '权限不足')
            return f(*args, **kwargs)
        return wrapper
    return decorator


@ai_bp.route('/api/ai/student-advice', methods=['POST'])
@_require_any_permission('ai:student_advice:self', 'ai:student_advice:all')
def student_advice():
    """生成学生个人学习建议"""
    data = request.get_json(force=True)
    student_id = data.get('student_id')
    term = data.get('term')

    # 学生只能生成自己的建议
    roles = g.current_user.get('roles', [])
    user_perms = g.current_user.get('permissions', [])
    if 'ai:student_advice:all' not in user_perms:
        student_id = g.current_user['user_id']

    if not student_id:
        raise BusinessError(ErrorCode.STUDENT_NOT_FOUND, '请指定学生ID')
    if 'teacher' in roles and 'admin' not in roles:
        teacher_scope_service.ensure_access(g.current_user, student_id=student_id)

    result = ai_service.generate_student_advice(
        student_id=student_id,
        term=term,
        operator_id=g.current_user['user_id'],
        trace_id=getattr(request, 'trace_id', ''),
        current_user=g.current_user,
    )

    audit_service.write(
        action='ai.student_advice',
        operator_id=g.current_user['user_id'],
        target_type='ai_analysis',
        target_id=str(result.get('analysis_id', '')),
        detail={'student_id': student_id, 'term': term, 'provider': result.get('provider')},
        trace_id=getattr(request, 'trace_id', ''),
    )
    db.session.commit()

    return success(result)


@ai_bp.route('/api/ai/class-overview', methods=['POST'])
@jwt_required
@permission_required('ai:class_overview')
def class_overview():
    """生成班级学情分析"""
    data = request.get_json(force=True)
    term = data.get('term')
    class_name = data.get('class_name')

    if not class_name:
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, '请指定班级名称')

    result = ai_service.generate_class_overview(
        term=term,
        class_name=class_name,
        operator_id=g.current_user['user_id'],
        trace_id=getattr(request, 'trace_id', ''),
        current_user=g.current_user,
    )

    audit_service.write(
        action='ai.class_overview',
        operator_id=g.current_user['user_id'],
        target_type='ai_analysis',
        target_id=str(result.get('analysis_id', '')),
        detail={'class_name': class_name, 'term': term, 'provider': result.get('provider')},
        trace_id=getattr(request, 'trace_id', ''),
    )
    db.session.commit()

    return success(result)


@ai_bp.route('/api/ai/exam-paper/analyze', methods=['POST'])
@jwt_required
@permission_required('ai:exam_analyze')
def exam_paper_analyze():
    """试卷考点分析"""
    data = request.get_json(force=True)
    title = data.get('title')
    subject = data.get('subject')
    exam_batch = data.get('exam_batch')
    paper_text = data.get('paper_text')

    if not paper_text:
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, '试卷文本不能为空')

    result = exam_analyzer.analyze_paper(
        title=title,
        subject=subject,
        exam_batch=exam_batch,
        paper_text=paper_text,
        operator_id=g.current_user['user_id'],
        trace_id=getattr(request, 'trace_id', ''),
    )

    audit_service.write(
        action='ai.exam_analyze',
        operator_id=g.current_user['user_id'],
        target_type='exam_paper',
        target_id=str(result.get('paper_id', '')),
        detail={'title': title, 'subject': subject, 'provider': result.get('provider')},
        trace_id=getattr(request, 'trace_id', ''),
    )
    db.session.commit()

    return success(result)


@ai_bp.route('/api/ai/exam-paper/analyze-image', methods=['POST'])
@jwt_required
@permission_required('ai:exam_analyze')
def exam_paper_analyze_image():
    """试卷图片考点分析（视觉 mock MVP）"""
    check_upload_rate_limit(g.current_user['user_id'], 'exam_image_analyze', limit=6, window_seconds=60)
    title = request.form.get('title')
    subject = request.form.get('subject')
    exam_batch = request.form.get('exam_batch')
    image_file = request.files.get('image')

    result = vision_exam_analyzer.analyze_image(
        title=title,
        subject=subject,
        exam_batch=exam_batch,
        image_file=image_file,
        operator_id=g.current_user['user_id'],
        trace_id=getattr(request, 'trace_id', ''),
    )

    audit_service.write(
        action='ai.exam_analyze_image',
        operator_id=g.current_user['user_id'],
        target_type='exam_paper',
        target_id=str(result.get('paper_id', '')),
        detail={'title': title, 'subject': subject, 'provider': result.get('provider')},
        trace_id=getattr(request, 'trace_id', ''),
    )
    db.session.commit()

    return success(result)


@ai_bp.route('/api/ai/exam-paper/ocr-preview', methods=['POST'])
@jwt_required
@permission_required('ai:exam_analyze')
def exam_paper_ocr_preview():
    """安全解码图片并返回可编辑 OCR 文字，不直接调用外部 AI。"""
    check_upload_rate_limit(g.current_user['user_id'], 'exam_ocr_preview', limit=6, window_seconds=60)
    result = ocr_service.preview_image(
        image_file=request.files.get('image'),
        operator_id=g.current_user['user_id'],
        trace_id=getattr(request, 'trace_id', ''),
    )
    return success(result)


@ai_bp.route('/api/ai/exam-paper/analyze-ocr', methods=['POST'])
@jwt_required
@permission_required('ai:exam_analyze')
def exam_paper_analyze_ocr():
    """使用用户确认/修正后的 OCR 文本进行结构化试卷分析。"""
    data = request.get_json(force=True) if request.data else {}
    result = ocr_service.analyze_confirmed(
        ocr_id=data.get('ocr_id'),
        title=data.get('title'),
        subject=data.get('subject'),
        exam_batch=data.get('exam_batch'),
        corrected_text=data.get('corrected_text'),
        operator_id=g.current_user['user_id'],
        trace_id=getattr(request, 'trace_id', ''),
    )
    return success(result)


@ai_bp.route('/api/ai/combined-advice', methods=['POST'])
@jwt_required
@permission_required('ai:combined_advice')
def combined_advice():
    """结合成绩和试卷的个性化复习建议"""
    data = request.get_json(force=True)
    student_id = data.get('student_id')
    paper_id = data.get('paper_id')
    term = data.get('term')

    # 学生只能生成自己的建议
    roles = g.current_user.get('roles', [])
    if 'student' in roles and 'teacher' not in roles and 'admin' not in roles:
        student_id = g.current_user['user_id']

    if not student_id:
        raise BusinessError(ErrorCode.STUDENT_NOT_FOUND, '请指定学生ID')
    if not paper_id:
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, '请指定试卷ID')

    result = exam_analyzer.generate_combined_advice(
        student_id=student_id,
        paper_id=paper_id,
        term=term,
        operator_id=g.current_user['user_id'],
        trace_id=getattr(request, 'trace_id', ''),
    )

    audit_service.write(
        action='ai.combined_advice',
        operator_id=g.current_user['user_id'],
        target_type='ai_analysis',
        target_id=str(result.get('analysis_id', '')),
        detail={'student_id': student_id, 'paper_id': paper_id, 'provider': result.get('provider')},
        trace_id=getattr(request, 'trace_id', ''),
    )
    db.session.commit()

    return success(result)


@ai_bp.route('/api/ai/history', methods=['GET'])
@jwt_required
@permission_required('ai:history:read')
def history():
    """查询 AI 分析历史"""
    filters = {
        'analysis_type': request.args.get('analysis_type'),
        'target_id': request.args.get('target_id'),
    }
    filters = {k: v for k, v in filters.items() if v}

    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)

    roles = g.current_user.get('roles', [])
    operator_id = g.current_user['user_id']

    result = ai_service.get_analysis_history(
        filters=filters,
        page=page,
        page_size=page_size,
        operator_roles=roles,
        operator_id=operator_id,
    )

    return success(result)


@ai_bp.route('/api/ai/history/<int:analysis_id>/feedback', methods=['POST'])
@jwt_required
def feedback(analysis_id):
    data = request.get_json(force=True) if request.data else {}
    return success(ai_service.submit_feedback(
        analysis_id=analysis_id,
        rating=data.get('rating'),
        comment=data.get('comment'),
        current_user=g.current_user,
        trace_id=getattr(request, 'trace_id', ''),
    ))
