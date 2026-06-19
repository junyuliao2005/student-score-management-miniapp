"""自动评语生成服务"""


def build_comment(avg_score, level_tag, warning_flags=None):
    """
    根据平均分、等级和预警状态生成自动评语。

    规则优先级：
    1. 同时命中低分+偏科预警
    2. 仅命中低分预警
    3. 仅命中偏科预警
    4. 未命中预警 + 优秀
    5. 未命中预警 + 良好/中等
    6. 未命中预警 + 及格/不及格
    """
    if warning_flags is None:
        warning_flags = []

    has_low_score = any(w.get('warning_type') == 'low_score' for w in warning_flags)
    has_subject_bias = any(w.get('warning_type') == 'subject_bias' for w in warning_flags)

    if has_low_score and has_subject_bias:
        return '存在低分与偏科风险，建议优先补齐短板科目。'
    if has_low_score:
        return '当前存在低分风险，建议及时复习薄弱章节。'
    if has_subject_bias:
        return '整体基础尚可，但学科表现不均衡，需强化弱势科目。'

    if level_tag == '优秀':
        return '基础扎实，继续保持。'
    if level_tag in ('良好', '中等'):
        return '整体表现稳定，建议继续提升细节题得分。'
    # 及格 / 不及格
    return '基础仍需巩固，建议制定阶段性提升计划。'
