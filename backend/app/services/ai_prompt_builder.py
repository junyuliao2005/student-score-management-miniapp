"""AI 提示词构建器"""
import json

from app.utils.privacy_sanitizer import (
    anonymize_student_list,
    anonymize_student_name,
    mask_sensitive_text,
)


def build_student_advice_prompt(student_name, scores_data, warnings):
    """
    构建学生学习建议提示词。
    scores_data: [{'course_name': ..., 'score': ..., 'level_tag': ..., 'rank_no': ...}]
    warnings: [{'warning_type': ..., 'course_name': ..., 'score': ...}]
    """
    score_lines = []
    for s in scores_data:
        line = f"- {s['course_name']}: {s['score']}分"
        if s.get('level_tag'):
            line += f" ({s['level_tag']})"
        if s.get('rank_no'):
            line += f", 排名第{s['rank_no']}名"
        score_lines.append(line)

    warning_lines = []
    for w in warnings:
        if w['warning_type'] == 'low_score':
            warning_lines.append(f"- 低分预警: {w.get('course_name', '某科目')} 成绩 {w.get('score', '?')} 低于预警线")
        elif w['warning_type'] == 'subject_bias':
            warning_lines.append(f"- 偏科预警: 最高分与最低分差距较大")

    prompt = f"""你是一位专业的学习分析师，请根据以下学生成绩数据给出个性化学习建议。

学生: {anonymize_student_name(student_name)}

成绩数据:
{chr(10).join(score_lines) if score_lines else '暂无成绩数据'}

预警信息:
{chr(10).join(warning_lines) if warning_lines else '无预警'}

请从以下维度进行分析，输出格式要求：
1. 【优势科目】: 列出表现最好的1-2门课程及原因
2. 【薄弱科目】: 列出需要重点提升的课程及原因
3. 【学习建议】: 给出3-5条具体可执行的学习建议
4. 【复习重点】: 指出需要重点关注的知识领域
5. 【鼓励评语】: 一段鼓励性的、积极的评语

要求：
- 建议要具体可执行，不要空泛
- 语气要鼓励、积极、客观
- 针对实际数据给出分析，不要泛泛而谈"""

    return mask_sensitive_text(prompt)


def build_class_overview_prompt(class_name, term, overview_data, top_students, weak_students):
    """
    构建班级学情分析提示词。
    overview_data: {student_count, avg_score, max_score, min_score, excellent_rate, pass_rate, low_score_count}
    top_students: [{'student_name': ..., 'avg_score': ...}]
    weak_students: [{'student_name': ..., 'avg_score': ..., 'warning_types': [...]}]
    """
    top_students = anonymize_student_list(top_students)
    weak_students = anonymize_student_list(weak_students)

    top_lines = []
    for s in top_students[:5]:
        top_lines.append(f"- {s['student_name']}: 平均分 {s['avg_score']}")

    weak_lines = []
    for s in weak_students[:5]:
        types = ', '.join(s.get('warning_types', []))
        weak_lines.append(f"- {s['student_name']}: 平均分 {s['avg_score']} ({types})")

    prompt = f"""你是一位资深教育分析师，请根据以下班级成绩数据进行学情分析。

班级: {class_name}
学期: {term}

班级概况:
- 学生人数: {overview_data.get('student_count', 0)}
- 平均分: {overview_data.get('avg_score', 0)}
- 最高分: {overview_data.get('max_score', 0)}
- 最低分: {overview_data.get('min_score', 0)}
- 优秀率: {overview_data.get('excellent_rate', 0):.1%}
- 及格率: {overview_data.get('pass_rate', 0):.1%}
- 低分人数: {overview_data.get('low_score_count', 0)}

优秀学生:
{chr(10).join(top_lines) if top_lines else '暂无'}

需要关注的学生:
{chr(10).join(weak_lines) if weak_lines else '暂无'}

请从以下维度进行分析，输出格式要求：
1. 【班级整体表现】: 对班级整体水平的评价
2. 【共性问题】: 班级普遍存在的问题（如有）
3. 【教学改进建议】: 给出3-5条教学改进方向
4. 【重点关注学生】: 列出需要特别关注的学生及原因

要求：
- 分析要基于数据，客观专业
- 建议要聚焦教学改进，具有可操作性"""

    return mask_sensitive_text(prompt)


def build_exam_paper_prompt(title, subject, paper_text, question_count):
    """
    构建试卷考点分析提示词。
    """
    prompt = f"""你是一位教学研究专家，请分析以下试卷的考点分布。

试卷标题: {title}
学科: {subject}
题目数量: {question_count if question_count else '待分析'}

试卷内容:
{paper_text}

请从以下维度进行分析，输出格式要求：
1. 【主要考点】: 列出本试卷涉及的主要考点（5-8个）
2. 【知识点分布】: 各知识点的题目分布情况
3. 【难度判断】: 整体难度评估（简单/中等/较难），并说明理由
4. 【易错点预测】: 学生容易出错的题目类型和知识点
5. 【复习建议】: 基于考点分析给出复习建议

要求：
- 考点分析要准确，基于试卷实际内容
- 难度判断要合理
- 复习建议要具体"""

    return mask_sensitive_text(prompt)


def build_combined_advice_prompt(student_name, scores_data, paper_key_points, paper_title):
    """
    构建结合成绩和试卷的个性化复习建议提示词。
    """
    score_lines = []
    for s in scores_data:
        score_lines.append(f"- {s['course_name']}: {s['score']}分 ({s.get('level_tag', '-')})")

    key_points_text = paper_key_points if isinstance(paper_key_points, str) else json.dumps(paper_key_points, ensure_ascii=False, indent=2)

    prompt = f"""你是一位个性化学习规划师，请结合学生当前成绩和试卷考点给出针对性复习建议。

学生: {anonymize_student_name(student_name)}

当前成绩:
{chr(10).join(score_lines) if score_lines else '暂无'}

试卷: {paper_title}
试卷考点分析:
{key_points_text}

请从以下维度给出建议，输出格式要求：
1. 【可能薄弱知识点】: 结合成绩和考点，判断学生可能薄弱的知识点
2. 【针对性复习建议】: 针对薄弱点给出具体复习方法
3. 【分阶段学习计划】: 制定短期（1周）、中期（1个月）学习计划
4. 【预期提升方向】: 指出最有提升空间的方向

要求：
- 建议要结合该学生的实际成绩水平
- 计划要具体可执行
- 语气要鼓励、积极"""

    return mask_sensitive_text(prompt)
