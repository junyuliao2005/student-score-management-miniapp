"""输入文本清洗与安全过滤"""
import re
import logging
from flask import current_app

logger = logging.getLogger(__name__)

# 危险提示词片段（防止 prompt injection）
DANGEROUS_PATTERNS = [
    r'ignore\s+(all\s+)?previous\s+instructions',
    r'忽略.{0,10}(之前|上面|以前).{0,10}(指令|提示|要求)',
    r'system\s*prompt',
    r'你的(系统|初始|原始)提示',
    r'假装你是',
    r'pretend\s+you\s+are',
    r'role\s*play\s+as',
    r'jailbreak',
    r'DAN\s+mode',
    r'do\s+anything\s+now',
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in DANGEROUS_PATTERNS]


def sanitize_input(text, max_chars=None):
    """
    清洗用户输入文本。
    返回 (cleaned_text, warnings)。
    如果文本为空，返回 (None, ['文本内容不能为空'])。
    """
    if text is None:
        return None, ['文本内容不能为空']

    cleaned = str(text).strip()
    if not cleaned:
        return None, ['文本内容不能为空']

    warnings = []

    # 获取最大字符限制
    if max_chars is None:
        try:
            max_chars = current_app.config.get('AI_MAX_INPUT_CHARS', 6000)
        except RuntimeError:
            max_chars = 6000

    # 截断过长文本
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars]
        warnings.append(f'文本已截断至 {max_chars} 字符')

    # 检测危险提示词
    try:
        safety_enabled = current_app.config.get('AI_SAFETY_ENABLED', True)
    except RuntimeError:
        safety_enabled = True

    if safety_enabled:
        for pattern in COMPILED_PATTERNS:
            if pattern.search(cleaned):
                logger.warning(f'检测到危险提示词片段: {pattern.pattern}')
                # 替换匹配内容
                cleaned = pattern.sub('[已过滤]', cleaned)
                warnings.append('检测到不安全内容，已自动过滤')

    # 去除多余空白
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    cleaned = re.sub(r' {2,}', ' ', cleaned)

    return cleaned, warnings


def validate_student_id(student_id):
    """校验学生ID格式"""
    if not student_id:
        return False, '学生ID不能为空'
    s = str(student_id).strip()
    if len(s) > 20:
        return False, '学生ID过长'
    return True, ''


def validate_term(term):
    """校验学期格式"""
    if not term:
        return True, ''  # 学期可选
    t = str(term).strip()
    if len(t) > 20:
        return False, '学期格式不正确'
    return True, ''
