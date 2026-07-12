"""试卷图片视觉考点分析 MVP。"""
import json
import os
import time

from flask import current_app

from app.extensions import db
from app.models.ai_analysis import AiAnalysis
from app.models.exam_paper import ExamPaper
from app.services import ai_provider
from app.services import ai_result_schema
from app.utils.errors import BusinessError, ErrorCode
from app.utils.file_validator import validate_image_file
from app.utils.privacy_sanitizer import mask_sensitive_text


def analyze_image(title, subject, exam_batch, image_file, operator_id, trace_id):
    """校验图片并返回 mock 视觉分析结果。"""
    title = (title or '').strip()
    subject = (subject or '').strip()
    exam_batch = (exam_batch or '').strip()

    if not title:
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, '试卷标题不能为空')
    if not subject:
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, '学科不能为空')
    if not exam_batch:
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, '考试批次不能为空')

    max_size_mb = current_app.config.get('AI_VISION_MAX_IMAGE_MB', 10)
    image_info = validate_image_file(image_file, max_size_mb=max_size_mb)
    image_bytes = image_file.read()
    image_file.seek(0)

    prompt = _build_vision_prompt(title, subject, exam_batch, image_info)

    start_time = time.time()
    api_result = ai_provider.call_vision_ai_api(prompt, image_bytes, image_info['mimetype'])
    duration_ms = int((time.time() - start_time) * 1000)

    usage = None
    if api_result is not None:
        result_text, duration_ms, usage = api_result
        provider_info = ai_provider.get_vision_provider_info()
        try:
            result_data = json.loads(result_text)
        except json.JSONDecodeError:
            result_data = {'recognized_summary': result_text}
    else:
        result_data = _generate_mock_result(title, subject, exam_batch, image_info)
        provider_info = ai_provider.get_mock_provider_info()
    result_data = ai_result_schema.normalize_ai_result('exam_paper_image', result_data)
    result_text = json.dumps(result_data, ensure_ascii=False, indent=2)
    token_used = ai_provider.total_tokens(usage)

    paper = ExamPaper(
        title=title,
        subject=subject,
        exam_batch=exam_batch,
        raw_text=result_data.get('recognized_summary', '')[:10000],
        key_points_json=json.dumps(result_data.get('key_points', []), ensure_ascii=False),
        difficulty_level=result_data.get('difficulty'),
        question_count=result_data.get('question_count'),
        created_by=operator_id,
        trace_id=trace_id,
    )
    db.session.add(paper)
    db.session.flush()

    input_snapshot = json.dumps({
        'title': title,
        'subject': subject,
        'exam_batch': exam_batch,
        'image_filename': image_info['filename'],
        'image_size': image_info['size'],
        'image_mimetype': image_info['mimetype'],
    }, ensure_ascii=False)

    record = AiAnalysis(
        analysis_type='exam_paper_image',
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
    return ai_provider.attach_result_metadata(result_data, provider_info, usage, trace_id)


def _build_vision_prompt(title, subject, exam_batch, image_info):
    return mask_sensitive_text(
        f"请识别并分析试卷图片。标题: {title}; 学科: {subject}; "
        f"考试批次: {exam_batch}; 文件名: {image_info['filename']}; "
        "输出识别摘要、主要考点、知识点分布、难度、易错点和复习建议。"
    )


def _generate_mock_result(title, subject, exam_batch, image_info):
    points = _subject_points(subject)
    size_kb = max(1, image_info['size'] // 1024)
    question_count = 8 if size_kb < 500 else 12 if size_kb < 2000 else 18
    difficulty = '中等' if question_count <= 12 else '较难'

    distribution_names = ['基础概念', '计算能力', '综合应用']
    if '英语' in subject:
        distribution_names = ['词汇语法', '阅读理解', '写作表达']
    elif '语文' in subject:
        distribution_names = ['文本理解', '古诗文', '写作表达']

    knowledge_distribution = [
        {'name': distribution_names[0], 'percent': 30},
        {'name': distribution_names[1], 'percent': 35},
        {'name': distribution_names[2], 'percent': 35},
    ]

    return {
        'recognized_summary': (
            f"根据上传的 {os.path.basename(image_info['filename'])} 演示识别结果，"
            f"《{title}》主要包含客观题、基础计算题和综合应用题，"
            f"适用于{exam_batch}阶段的{subject}学情诊断。"
        ),
        'key_points': points[:5],
        'knowledge_distribution': knowledge_distribution,
        'distribution': [f"{item['name']}: {item['percent']}%" for item in knowledge_distribution],
        'difficulty': difficulty,
        'difficulty_reason': '基础题和综合题比例较均衡，部分题目需要多步骤推理。',
        'error_prone_points': ['审题遗漏条件', '计算符号错误', '综合题步骤不完整'],
        'error_prone': ['审题遗漏条件', '计算符号错误', '综合题步骤不完整'],
        'review_suggestions': ['复习核心公式与基础概念', '整理错题并按知识点归类', '加强综合题分步训练'],
        'review_advice': ['复习核心公式与基础概念', '整理错题并按知识点归类', '加强综合题分步训练'],
        'question_count': question_count,
        'provider': 'mock',
        'is_mock': True,
    }


def _subject_points(subject):
    if '数学' in subject:
        return ['函数性质', '方程求解', '应用题建模', '计算能力', '综合推理']
    if '英语' in subject:
        return ['词汇运用', '语法结构', '阅读理解', '写作表达', '语篇分析']
    if '语文' in subject:
        return ['现代文阅读', '古诗文理解', '语言运用', '写作立意', '文本分析']
    if '物理' in subject:
        return ['力学模型', '电路分析', '实验探究', '公式应用', '图像理解']
    return ['基础概念', '计算能力', '综合应用', '分析推理', '规范表达']
