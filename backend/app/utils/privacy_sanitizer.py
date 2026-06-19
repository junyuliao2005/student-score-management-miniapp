"""隐私脱敏工具。

用于真实 AI 调用、审计详情和日志等场景，避免把手机号、身份证、token
等敏感信息传出系统边界。这里不改变业务数据，只处理即将发送或记录的文本。
"""
import re


SENSITIVE_PATTERNS = [
    (re.compile(r'1[3-9]\d{9}'), '[手机号已脱敏]'),
    (re.compile(r'\b\d{17}[\dXx]\b'), '[身份证已脱敏]'),
    (re.compile(r'(?i)(bearer\s+)[a-z0-9._\-]+'), r'\1[Token已脱敏]'),
    (re.compile(r'(?i)(token|api[_-]?key|password|passwd|pwd)\s*[:=]\s*[^\s,;，；]+'), r'\1=[已脱敏]'),
]


def mask_sensitive_text(value):
    """对文本中的常见敏感信息做脱敏。"""
    text = str(value or '')
    for pattern, replacement in SENSITIVE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def anonymize_student_name(value=''):
    """AI prompt 中弱化学生姓名，不向真实模型暴露真实姓名。"""
    return '该学生'


def anonymize_student_list(items, name_key='student_name'):
    """把学生列表中的姓名替换为学生A/学生B，保留成绩等必要学习数据。"""
    safe_items = []
    for index, item in enumerate(items or []):
        safe = dict(item)
        if name_key in safe:
            safe[name_key] = f"学生{chr(ord('A') + min(index, 25))}"
        safe_items.append(safe)
    return safe_items
