"""
试卷分析服务
协调试卷存储、考点分析、结果持久化。
"""
import json
import logging
import re
import time

from flask import current_app
from app.extensions import db
from app.models.exam_paper import ExamPaper
from app.models.ai_analysis import AiAnalysis
from app.models.score import Score
from app.models.course import Course
from app.services import ai_provider
from app.services import ai_mock_service
from app.services import ai_prompt_builder
from app.utils.text_sanitizer import sanitize_input
from app.utils.errors import BusinessError, ErrorCode

logger = logging.getLogger(__name__)


def analyze_paper(title, subject, exam_batch, paper_text, operator_id, trace_id):
    """
    分析试卷考点。
    1. 清洗输入
    2. 估算题目数量
    3. 调用 AI / mock 分析
    4. 保存到 exam_paper 表
    5. 保存到 ai_analysis 表
    """
    # 清洗输入
    cleaned_text, warnings = sanitize_input(paper_text)
    if cleaned_text is None:
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, '试卷文本不能为空')

    if not title or not title.strip():
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, '试卷标题不能为空')
    if not subject or not subject.strip():
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, '学科不能为空')

    # 估算题目数量
    question_count = _estimate_question_count(cleaned_text)

    # 构建 prompt
    prompt = ai_prompt_builder.build_exam_paper_prompt(
        title.strip(), subject.strip(), cleaned_text, question_count
    )

    # 尝试真实 API
    start_time = time.time()
    api_result = ai_provider.call_ai_api(prompt)
    duration_ms = int((time.time() - start_time) * 1000)

    if api_result is not None:
        result_text, duration_ms, token_used = api_result
        provider_info = ai_provider.get_provider_info()
        try:
            result_data = json.loads(result_text)
        except json.JSONDecodeError:
            result_data = {'raw_text': result_text}
    else:
        result_data = ai_mock_service.generate_exam_analysis(
            title.strip(), subject.strip(), cleaned_text, question_count
        )
        result_text = json.dumps(result_data, ensure_ascii=False, indent=2)
        provider_info = ai_provider.get_mock_provider_info()
        token_used = None

    # 保存试卷记录
    paper = ExamPaper(
        title=title.strip(),
        subject=subject.strip(),
        exam_batch=exam_batch.strip() if exam_batch else None,
        raw_text=cleaned_text[:10000],  # 限制存储长度
        key_points_json=json.dumps(result_data.get('key_points', []), ensure_ascii=False),
        difficulty_level=result_data.get('difficulty'),
        question_count=result_data.get('question_count', question_count),
        created_by=operator_id,
        trace_id=trace_id,
    )
    db.session.add(paper)
    db.session.flush()

    # 保存分析记录
    input_snapshot = json.dumps({
        'title': title,
        'subject': subject,
        'text_length': len(cleaned_text),
        'question_count': question_count,
    }, ensure_ascii=False)

    record = AiAnalysis(
        analysis_type='exam_paper',
        target_id=str(paper.paper_id),
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

    result_data['paper_id'] = paper.paper_id
    result_data['analysis_id'] = record.analysis_id
    result_data['provider'] = provider_info['provider']
    result_data['is_mock'] = provider_info['is_mock']

    return result_data


def generate_combined_advice(student_id, paper_id, term, operator_id, trace_id):
    """
    结合学生成绩和试卷考点生成个性化复习建议。
    """
    # 查询学生
    from app.models.user import User
    student = User.query.filter_by(user_id=student_id).first()
    if not student:
        raise BusinessError(ErrorCode.STUDENT_NOT_FOUND, '学生不存在',
                            data={'student_id': student_id})

    # 查询试卷
    paper = ExamPaper.query.filter_by(paper_id=paper_id).first()
    if not paper:
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, '试卷不存在',
                            data={'paper_id': paper_id})

    # 查询成绩
    query = Score.query.filter_by(student_id=student_id, status=1)
    if term:
        query = query.join(Course, Score.course_id == Course.course_id) \
            .filter(Course.term == term)
    scores = query.all()

    scores_data = []
    for s in scores:
        scores_data.append({
            'course_name': s.course.course_name if s.course else s.course_id,
            'score': float(s.score),
            'level_tag': s.level_tag,
        })

    # 解析试卷考点
    key_points = paper.key_points_json

    # 构建 prompt
    prompt = ai_prompt_builder.build_combined_advice_prompt(
        student.real_name, scores_data, key_points, paper.title
    )

    input_snapshot = json.dumps({
        'student_id': student_id,
        'paper_id': paper_id,
        'term': term,
        'scores_count': len(scores_data),
    }, ensure_ascii=False)

    # 尝试真实 API
    start_time = time.time()
    api_result = ai_provider.call_ai_api(prompt)
    duration_ms = int((time.time() - start_time) * 1000)

    if api_result is not None:
        result_text, duration_ms, token_used = api_result
        provider_info = ai_provider.get_provider_info()
    else:
        mock_result = ai_mock_service.generate_combined_advice(
            student.real_name, scores_data, key_points, paper.title
        )
        result_text = json.dumps(mock_result, ensure_ascii=False, indent=2)
        provider_info = ai_provider.get_mock_provider_info()
        token_used = None

    # 保存记录
    record = AiAnalysis(
        analysis_type='combined',
        target_id=f'{student_id}_{paper_id}',
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

    try:
        result_data = json.loads(result_text)
    except json.JSONDecodeError:
        result_data = {'raw_text': result_text}

    result_data['analysis_id'] = record.analysis_id
    result_data['provider'] = provider_info['provider']
    result_data['is_mock'] = provider_info['is_mock']

    return result_data


def _estimate_question_count(text):
    """估算试卷题目数量"""
    # 匹配题号模式: 1. 2. 3. 或 一、二、三、或 1、2、
    patterns = [
        r'(?:^|\n)\s*\d+[\.、．]\s*\S',  # 1. 或 1、
        r'(?:^|\n)\s*[一二三四五六七八九十]+[、．.]\s*\S',  # 一、
    ]
    max_count = 0
    for pattern in patterns:
        matches = re.findall(pattern, text)
        max_count = max(max_count, len(matches))

    if max_count == 0:
        max_count = max(5, len(text) // 300)

    return max_count
