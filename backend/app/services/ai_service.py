"""
AI 服务主入口
协调 prompt 构建、provider 调用、mock 回退、结果存储。
"""
import json
import logging
import time
from sqlalchemy import and_, or_

from flask import current_app
from app.extensions import db
from app.models.user import User
from app.models.score import Score
from app.models.course import Course
from app.models.ai_analysis import AiAnalysis
from app.models.ai_feedback import AiAnalysisFeedback
from app.models.exam_paper import ExamPaper
from app.services import ai_provider, teacher_scope_service, exam_publish_service, audit_service
from app.services import ai_mock_service
from app.services import ai_prompt_builder
from app.services import ai_result_schema
from app.services import warning_calculator
from app.utils.text_sanitizer import sanitize_input, validate_student_id
from app.utils.errors import BusinessError, ErrorCode

logger = logging.getLogger(__name__)


def generate_student_advice(student_id, term, operator_id, trace_id, current_user=None):
    """
    生成学生个人学习建议。
    返回 dict 包含分析结果和元数据。
    """
    # 校验输入
    valid, msg = validate_student_id(student_id)
    if not valid:
        raise BusinessError(ErrorCode.STUDENT_NOT_FOUND, msg)

    # 查询学生信息
    student = User.query.filter_by(user_id=student_id).first()
    if not student:
        raise BusinessError(ErrorCode.STUDENT_NOT_FOUND, '学生不存在',
                            data={'student_id': student_id})

    # 查询成绩
    query = Score.query.filter_by(student_id=student_id, status=1)
    if term:
        query = query.join(Course, Score.course_id == Course.course_id) \
            .filter(Course.term == term)
    roles = (current_user or {}).get('roles') or []
    is_student_self = 'student' in roles and 'teacher' not in roles and 'admin' not in roles
    if is_student_self:
        published = exam_publish_service.get_published_settings_for_student(
            student_id, {'term': term} if term else {},
        )
        if not published:
            scores = []
        else:
            if not term:
                query = query.join(Course, Score.course_id == Course.course_id)
            allowed = [
                and_(Course.term == setting.term, Score.exam_batch == setting.exam_batch)
                for setting in published
            ]
            scores = query.filter(or_(*allowed)).all()
    else:
        if current_user is not None:
            query = teacher_scope_service.apply_score_scope(query, current_user)
        scores = query.all()

    scores_data = []
    for s in scores:
        scores_data.append({
            'course_name': s.course.course_name if s.course else s.course_id,
            'score': float(s.score),
            'level_tag': s.level_tag,
            'rank_no': s.rank_no,
            'avg_score': float(s.avg_score) if s.avg_score else None,
        })

    # 查询预警
    warnings = []
    if term and not is_student_self:
        warning_result = warning_calculator.build_warnings(student_id, term)
        warnings = warning_result if isinstance(warning_result, list) else []

    # 构建 prompt
    prompt = ai_prompt_builder.build_student_advice_prompt(
        student.real_name, scores_data, warnings
    )

    # 构建输入快照
    input_snapshot = json.dumps({
        'student_id': student_id,
        'student_name': student.real_name,
        'term': term,
        'scores_count': len(scores_data),
        'warnings_count': len(warnings),
    }, ensure_ascii=False)

    # 尝试真实 API，失败则回退 mock
    start_time = time.time()
    api_result = ai_provider.call_ai_api(prompt)
    duration_ms = int((time.time() - start_time) * 1000)

    usage = None
    if api_result is not None:
        result_text, duration_ms, usage = api_result
        provider_info = ai_provider.get_provider_info()
        try:
            result_data = json.loads(result_text)
        except json.JSONDecodeError:
            result_data = {'raw_text': result_text}
    else:
        # Mock 模式
        mock_result = ai_mock_service.generate_student_advice(
            student.real_name, scores_data, warnings
        )
        result_data = mock_result
        provider_info = ai_provider.get_mock_provider_info()
    result_data = ai_result_schema.normalize_ai_result('student_advice', result_data)
    result_text = json.dumps(result_data, ensure_ascii=False, indent=2)
    token_used = ai_provider.total_tokens(usage)

    # 保存分析记录
    record = AiAnalysis(
        analysis_type='student_advice',
        target_id=student_id,
        input_snapshot=input_snapshot,
        prompt_text=prompt if current_app.config.get('AI_SAVE_PROMPT', False) else None,
        result_text=result_text,
        provider=provider_info['provider'],
        model_name=provider_info.get('model'),
        status='success',
        token_used=token_used,
        duration_ms=duration_ms,
        created_by=operator_id,
        trace_id=trace_id,
    )
    db.session.add(record)
    db.session.commit()

    result_data['analysis_id'] = record.analysis_id
    return ai_provider.attach_result_metadata(result_data, provider_info, usage, trace_id)


def generate_class_overview(term, class_name, operator_id, trace_id, current_user):
    """
    生成班级学情分析。
    """
    if not class_name:
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, '班级名称不能为空')
    teacher_scope_service.ensure_access(current_user, class_name=class_name)

    # 查询班级学生
    students = User.query.filter_by(class_name=class_name, status=1).all()
    if not students:
        raise BusinessError(ErrorCode.STUDENT_NOT_FOUND, '该班级无学生',
                            data={'class_name': class_name})

    student_ids = [s.user_id for s in students]

    # 查询成绩
    query = Score.query.filter(
        Score.student_id.in_(student_ids),
        Score.status == 1,
    )
    query = teacher_scope_service.apply_score_scope(query, current_user)
    if term:
        query = query.join(Course, Score.course_id == Course.course_id) \
            .filter(Course.term == term)
    scores = query.all()

    # 计算概览
    if scores:
        all_scores = [float(s.score) for s in scores]
        avg_score = sum(all_scores) / len(all_scores)
        max_score = max(all_scores)
        min_score = min(all_scores)

        # 按学生聚合
        student_scores = {}
        for s in scores:
            if s.student_id not in student_scores:
                student_scores[s.student_id] = []
            student_scores[s.student_id].append(float(s.score))

        student_avgs = []
        for sid, scrs in student_scores.items():
            student_avgs.append({
                'student_id': sid,
                'avg_score': sum(scrs) / len(scrs),
            })

        excellent_count = sum(1 for a in student_avgs if a['avg_score'] >= 90)
        pass_count = sum(1 for a in student_avgs if a['avg_score'] >= 60)
        low_count = sum(1 for a in student_avgs if a['avg_score'] < 60)

        overview_data = {
            'student_count': len(students),
            'score_count': len(scores),
            'avg_score': round(avg_score, 2),
            'max_score': round(max_score, 2),
            'min_score': round(min_score, 2),
            'excellent_rate': excellent_count / len(student_avgs) if student_avgs else 0,
            'pass_rate': pass_count / len(student_avgs) if student_avgs else 0,
            'low_score_count': low_count,
        }

        # 优秀学生和薄弱学生
        sorted_avgs = sorted(student_avgs, key=lambda x: x['avg_score'], reverse=True)
        top_students = []
        for a in sorted_avgs[:5]:
            student = next((s for s in students if s.user_id == a['student_id']), None)
            top_students.append({
                'student_name': student.real_name if student else a['student_id'],
                'avg_score': round(a['avg_score'], 2),
            })

        weak_students = []
        for a in sorted_avgs[-5:]:
            student = next((s for s in students if s.user_id == a['student_id']), None)
            warning_types = []
            if a['avg_score'] < 60:
                warning_types.append('低分预警')
            weak_students.append({
                'student_name': student.real_name if student else a['student_id'],
                'avg_score': round(a['avg_score'], 2),
                'warning_types': warning_types,
            })
    else:
        overview_data = {
            'student_count': len(students),
            'score_count': 0,
            'avg_score': 0, 'max_score': 0, 'min_score': 0,
            'excellent_rate': 0, 'pass_rate': 0, 'low_score_count': 0,
        }
        top_students = []
        weak_students = []

    # 构建 prompt
    prompt = ai_prompt_builder.build_class_overview_prompt(
        class_name, term, overview_data, top_students, weak_students
    )

    input_snapshot = json.dumps({
        'class_name': class_name,
        'term': term,
        'student_count': len(students),
    }, ensure_ascii=False)

    # 尝试真实 API
    start_time = time.time()
    api_result = ai_provider.call_ai_api(prompt)
    duration_ms = int((time.time() - start_time) * 1000)

    usage = None
    if api_result is not None:
        result_text, duration_ms, usage = api_result
        provider_info = ai_provider.get_provider_info()
        try:
            result_data = json.loads(result_text)
        except json.JSONDecodeError:
            result_data = {'raw_text': result_text}
    else:
        mock_result = ai_mock_service.generate_class_overview(
            class_name, term, overview_data, top_students, weak_students
        )
        result_data = mock_result
        provider_info = ai_provider.get_mock_provider_info()
    result_data = ai_result_schema.normalize_ai_result('class_overview', result_data)
    result_text = json.dumps(result_data, ensure_ascii=False, indent=2)
    token_used = ai_provider.total_tokens(usage)

    # 保存记录
    record = AiAnalysis(
        analysis_type='class_overview',
        target_id=class_name,
        input_snapshot=input_snapshot,
        prompt_text=prompt if current_app.config.get('AI_SAVE_PROMPT', False) else None,
        result_text=result_text,
        provider=provider_info['provider'],
        model_name=provider_info.get('model'),
        status='success',
        token_used=token_used,
        duration_ms=duration_ms,
        created_by=operator_id,
        trace_id=trace_id,
    )
    db.session.add(record)
    db.session.commit()

    result_data['analysis_id'] = record.analysis_id
    return ai_provider.attach_result_metadata(result_data, provider_info, usage, trace_id)


def get_analysis_history(filters, page, page_size, operator_roles, operator_id):
    """
    查询 AI 分析历史。
    - 学生只能看自己的
    - 教师看自己创建的
    - 管理员看全部
    """
    query = AiAnalysis.query

    # 权限过滤
    if 'admin' not in operator_roles:
        if 'student' in operator_roles:
            query = query.filter(
                AiAnalysis.analysis_type == 'student_advice',
                AiAnalysis.target_id == operator_id,
            )
        else:
            query = query.filter(AiAnalysis.created_by == operator_id)

    if filters.get('analysis_type'):
        query = query.filter(AiAnalysis.analysis_type == filters['analysis_type'])
    if filters.get('target_id'):
        query = query.filter(AiAnalysis.target_id == filters['target_id'])

    total = query.count()
    total_pages = (total + page_size - 1) // page_size

    items = query.order_by(AiAnalysis.created_at.desc()) \
        .offset((page - 1) * page_size) \
        .limit(page_size) \
        .all()

    feedback_map = {
        row.analysis_id: row
        for row in AiAnalysisFeedback.query.filter(
            AiAnalysisFeedback.user_id == operator_id,
            AiAnalysisFeedback.analysis_id.in_([item.analysis_id for item in items]),
        ).all()
    } if items else {}
    result_items = []
    for item in items:
        data = item.to_dict()
        try:
            parsed_result = json.loads(item.result_text)
        except (TypeError, json.JSONDecodeError):
            parsed_result = {'summary': str(item.result_text or '')[:500]}
        data['result'] = parsed_result
        feedback = feedback_map.get(item.analysis_id)
        data['my_feedback'] = feedback.to_dict() if feedback else None
        result_items.append(data)
    return {
        'list': result_items,
        'page': page,
        'page_size': page_size,
        'total': total,
        'total_pages': total_pages,
    }


def submit_feedback(analysis_id, rating, comment, current_user, trace_id=''):
    allowed_ratings = {'useful', 'neutral', 'not_useful'}
    if rating not in allowed_ratings:
        raise BusinessError(ErrorCode.INVALID_PARAMETER, '反馈选项无效')
    analysis = AiAnalysis.query.filter_by(analysis_id=analysis_id).first()
    if not analysis or not _can_view_analysis(analysis, current_user):
        raise BusinessError(ErrorCode.PERMISSION_DENIED, '无权评价该分析记录')
    user_id = current_user.get('user_id')
    feedback = AiAnalysisFeedback.query.filter_by(analysis_id=analysis_id, user_id=user_id).first()
    if not feedback:
        feedback = AiAnalysisFeedback(analysis_id=analysis_id, user_id=user_id, rating=rating)
        db.session.add(feedback)
    feedback.rating = rating
    feedback.comment = str(comment or '').strip()[:500] or None
    audit_service.write(
        action='ai.feedback',
        operator_id=user_id,
        target_type='ai_analysis',
        target_id=analysis_id,
        detail={'rating': rating},
        trace_id=trace_id,
    )
    db.session.commit()
    return feedback.to_dict()


def _can_view_analysis(analysis, current_user):
    roles = (current_user or {}).get('roles') or []
    user_id = (current_user or {}).get('user_id')
    if 'admin' in roles:
        return True
    if 'student' in roles:
        return analysis.analysis_type == 'student_advice' and analysis.target_id == user_id
    return analysis.created_by == user_id
