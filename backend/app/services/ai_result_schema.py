"""Lightweight server-side schemas for AI JSON output."""
from copy import deepcopy


SCHEMAS = {
    'student_advice': {
        'strengths': '',
        'weaknesses': '',
        'advice': [],
        'focus': '',
        'encouragement': '',
    },
    'class_overview': {
        'overall': '',
        'problems': [],
        'teaching_advice': [],
        'focus_students': [],
    },
    'exam_paper': {
        'recognized_summary': '',
        'key_points': [],
        'distribution': [],
        'knowledge_distribution': [],
        'difficulty': '不确定',
        'difficulty_reason': '',
        'error_prone': [],
        'error_prone_points': [],
        'review_advice': [],
        'review_suggestions': [],
        'question_count': None,
    },
    'combined_advice': {
        'weak_points': [],
        'targeted_advice': [],
        'study_plan': {'short': '', 'medium': ''},
        'improvement_direction': '',
    },
    'exam_paper_image': {
        'subject': '',
        'recognized_text': '',
        'recognized_summary': '',
        'questions': [],
        'question_type': [],
        'knowledge_points': [],
        'key_points': [],
        'knowledge_distribution': [],
        'difficulty': '不确定',
        'suspected_errors': [],
        'weak_points': [],
        'review_advice': [],
        'confidence': None,
        'warnings': [],
    },
}


def normalize_ai_result(schema_name, value):
    """Validate top-level JSON object and fill missing/type-invalid fields."""
    if not isinstance(value, dict):
        value = {'raw_text': str(value or '')}
    schema = SCHEMAS.get(schema_name)
    if not schema:
        return dict(value)
    result = dict(value)
    for key, default in schema.items():
        current = result.get(key)
        if current is None or not _same_shape(current, default):
            result[key] = deepcopy(default)
    return result


def _same_shape(value, default):
    if default is None:
        return True
    if isinstance(default, list):
        return isinstance(value, list)
    if isinstance(default, dict):
        return isinstance(value, dict)
    if isinstance(default, str):
        return isinstance(value, str)
    if isinstance(default, bool):
        return isinstance(value, bool)
    if isinstance(default, (int, float)):
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return True
