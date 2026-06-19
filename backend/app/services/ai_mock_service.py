"""
AI Mock 服务
基于真实成绩数据生成合理的分析结果，无需外部 API。
"""
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def generate_student_advice(student_name, scores_data, warnings):
    """
    基于真实成绩数据生成学生学习建议。
    scores_data: [{'course_name': ..., 'score': ..., 'level_tag': ..., 'rank_no': ...}]
    warnings: [{'warning_type': ..., 'course_name': ..., 'score': ...}]
    """
    if not scores_data:
        return _build_result(
            strengths='暂无成绩数据，无法判断优势科目。',
            weaknesses='暂无成绩数据，无法判断薄弱科目。',
            advice=['请先录入成绩数据，以便进行学情分析。'],
            focus='待成绩录入后再进行分析。',
            encouragement=f'{student_name}同学，请先完成成绩录入，系统将为你生成个性化学习建议。',
        )

    # 分析成绩数据
    sorted_scores = sorted(scores_data, key=lambda x: x.get('score', 0), reverse=True)
    best = sorted_scores[0]
    worst = sorted_scores[-1]
    avg = sum(s.get('score', 0) for s in scores_data) / len(scores_data)

    # 优势科目
    strengths_parts = []
    for s in sorted_scores[:2]:
        if s.get('score', 0) >= 80:
            strengths_parts.append(f"{s['course_name']}（{s['score']}分，{s.get('level_tag', '')}）")
    strengths = '、'.join(strengths_parts) if strengths_parts else f"{best['course_name']}（{best['score']}分）相对较好"

    # 薄弱科目
    weaknesses_parts = []
    for s in sorted_scores:
        if s.get('score', 0) < 60:
            weaknesses_parts.append(f"{s['course_name']}（{s['score']}分，不及格）")
        elif s.get('score', 0) < 70:
            weaknesses_parts.append(f"{s['course_name']}（{s['score']}分，及格线附近）")
    weaknesses = '、'.join(weaknesses_parts) if weaknesses_parts else f"{worst['course_name']}（{worst['score']}分）有提升空间"

    # 学习建议
    advice = []
    has_low = any(w['warning_type'] == 'low_score' for w in warnings)
    has_bias = any(w['warning_type'] == 'subject_bias' for w in warnings)

    if has_low:
        low_courses = [w.get('course_name', '薄弱科目') for w in warnings if w['warning_type'] == 'low_score']
        advice.append(f"优先复习{'、'.join(low_courses)}，从基础概念入手，确保及格。")
        advice.append("每天安排固定时间进行薄弱科目练习，循序渐进。")

    if has_bias:
        advice.append(f"在保持{best['course_name']}优势的同时，增加{worst['course_name']}的学习时间。")
        advice.append("采用交叉学习法，避免长时间只学一门课程。")

    if avg >= 90:
        advice.append("保持当前学习节奏，适当挑战更高难度的题目。")
    elif avg >= 80:
        advice.append("注重细节题的得分，减少粗心失误。")
    elif avg >= 70:
        advice.append("系统梳理各科知识点，查漏补缺。")
    else:
        advice.append("制定每日学习计划，保证基本学习时间。")

    if not advice:
        advice.append("继续保持当前学习状态，稳步提升。")

    # 复习重点
    low_courses = [s['course_name'] for s in sorted_scores if s.get('score', 0) < 80]
    if low_courses:
        focus = f"重点复习{'、'.join(low_courses)}，兼顾其他科目。"
    else:
        focus = "各科均衡发展，适当拓展高难度内容。"

    # 鼓励评语
    if avg >= 90:
        encouragement = f"{student_name}同学，你的成绩非常优秀！继续保持这份努力和专注，相信你会取得更好的成绩。加油！"
    elif avg >= 80:
        encouragement = f"{student_name}同学，你的基础很扎实，只要再加把劲，突破细节题的得分，成绩一定会有明显提升！"
    elif avg >= 70:
        encouragement = f"{student_name}同学，你有很大的进步空间！只要坚持每天复习，合理安排时间，成绩一定会稳步提高。"
    elif avg >= 60:
        encouragement = f"{student_name}同学，不要气馁！每个人都有自己的学习节奏，只要坚持努力，一定会看到进步。"
    else:
        encouragement = f"{student_name}同学，学习是一个循序渐进的过程。从基础开始，一步一步来，老师相信你一定可以做到！"

    return _build_result(
        strengths=strengths,
        weaknesses=weaknesses,
        advice=advice,
        focus=focus,
        encouragement=encouragement,
    )


def generate_class_overview(class_name, term, overview_data, top_students, weak_students):
    """
    基于真实班级数据生成学情分析。
    """
    student_count = overview_data.get('student_count', 0)
    avg_score = overview_data.get('avg_score', 0)
    excellent_rate = overview_data.get('excellent_rate', 0)
    pass_rate = overview_data.get('pass_rate', 0)
    low_count = overview_data.get('low_score_count', 0)

    # 班级整体表现
    if avg_score >= 85:
        overall = f"班级整体表现优秀，平均分{avg_score:.1f}分，优秀率{excellent_rate:.1%}，处于较高水平。"
    elif avg_score >= 75:
        overall = f"班级整体表现良好，平均分{avg_score:.1f}分，及格率{pass_rate:.1%}，仍有提升空间。"
    elif avg_score >= 60:
        overall = f"班级整体表现一般，平均分{avg_score:.1f}分，及格率{pass_rate:.1%}，需要加强教学。"
    else:
        overall = f"班级整体成绩偏低，平均分{avg_score:.1f}分，需要重点关注学困生。"

    # 共性问题
    problems = []
    if low_count > student_count * 0.3:
        problems.append(f"低分学生比例较高（{low_count}人），需要加强基础知识教学。")
    if excellent_rate < 0.2 and student_count > 0:
        problems.append("优秀率偏低，需要增加拓展性内容的教学。")
    if pass_rate < 0.8 and student_count > 0:
        problems.append(f"及格率仅{pass_rate:.1%}，需要关注学困生的辅导。")
    if not problems:
        problems.append("暂无明显共性问题，继续保持。")

    # 教学改进建议
    teaching_advice = []
    if low_count > 0:
        teaching_advice.append(f"对{low_count}名低分学生进行一对一辅导，制定个性化补习计划。")
    if avg_score < 80:
        teaching_advice.append("加强课堂练习和随堂测验，及时发现学生知识盲点。")
    if excellent_rate < 0.3:
        teaching_advice.append("增加拓展性题目和思考题，激发优秀学生的潜力。")
    teaching_advice.append("定期进行阶段性测试，动态调整教学进度。")
    teaching_advice.append("建立学习小组，促进学生互助学习。")

    # 重点关注学生
    focus_students = []
    for s in weak_students[:5]:
        types = '、'.join(s.get('warning_types', []))
        focus_students.append(f"{s['student_name']}（平均分{s['avg_score']:.1f}，{types}）")
    if not focus_students:
        focus_students.append("暂无需要特别关注的学生。")

    return {
        'overall': overall,
        'problems': problems,
        'teaching_advice': teaching_advice,
        'focus_students': focus_students,
        'provider': 'mock',
        'is_mock': True,
    }


def generate_exam_analysis(title, subject, paper_text, question_count):
    """
    基于试卷文本规则分析考点（mock 模式）。
    通过关键词、题号、文本长度等规则模拟考点分析。
    """
    text_lower = paper_text.lower()
    text_len = len(paper_text)

    # 基于学科的默认考点
    subject_key_points = {
        '数学': ['函数与方程', '几何证明', '概率统计', '数列', '不等式', '三角函数'],
        '英语': ['阅读理解', '完形填空', '语法填空', '写作表达', '词汇运用'],
        '语文': ['阅读理解', '古诗文鉴赏', '作文', '语言运用', '文学常识'],
        '物理': ['力学', '电磁学', '光学', '热学', '实验设计'],
        '化学': ['化学反应', '有机化学', '化学实验', '元素周期', '化学计算'],
        '计算机': ['数据结构', '算法设计', '程序设计', '数据库', '网络基础'],
        'python': ['基础语法', '数据类型', '函数', '面向对象', '文件操作', '异常处理'],
    }

    # 根据学科选择考点
    subject_lower = subject.lower()
    matched_points = []
    for key, points in subject_key_points.items():
        if key in subject_lower or subject_lower in key:
            matched_points = points
            break

    if not matched_points:
        matched_points = ['基础概念', '综合应用', '分析推理', '实践操作']

    # 根据文本内容调整
    key_points = []
    for point in matched_points[:6]:
        # 检查关键词是否在试卷中出现
        relevance = '高频' if any(kw in text_lower for kw in point.lower().split()) else '中频'
        key_points.append({
            'name': point,
            'relevance': relevance,
            'question_count': max(1, text_len // 500),
        })

    # 估算题目数量
    if question_count is None:
        # 通过题号模式估算
        import re
        numbers = re.findall(r'(?:^|\n)\s*(\d+)[\.、．]', paper_text)
        question_count = len(numbers) if numbers else max(5, text_len // 200)

    # 难度判断
    if text_len > 4000:
        difficulty = '较难'
        difficulty_reason = '试卷内容丰富，题量较大，综合性较强。'
    elif text_len > 2000:
        difficulty = '中等'
        difficulty_reason = '试卷难度适中，涵盖主要知识点。'
    else:
        difficulty = '简单'
        difficulty_reason = '试卷内容较少，以基础题为主。'

    # 易错点
    error_prone = []
    if '证明' in paper_text or '推导' in paper_text:
        error_prone.append('证明题逻辑不严密，步骤不完整')
    if '计算' in paper_text or '求' in paper_text:
        error_prone.append('计算题粗心导致结果错误')
    if '分析' in paper_text or '论述' in paper_text:
        error_prone.append('分析论述题要点不全面')
    if not error_prone:
        error_prone = ['基础概念混淆', '审题不仔细', '答题时间分配不合理']

    # 知识点分布
    distribution = []
    for i, kp in enumerate(key_points):
        distribution.append(f"{kp['name']}: {kp['question_count']}题")

    # 复习建议
    review_advice = [
        f"重点复习{key_points[0]['name']}和{key_points[1]['name']}相关内容。",
        "针对易错题型进行专项训练。",
        "系统梳理知识框架，注意知识点之间的联系。",
        "多做历年真题，熟悉出题规律。",
    ]

    return {
        'key_points': key_points,
        'distribution': distribution,
        'difficulty': difficulty,
        'difficulty_reason': difficulty_reason,
        'error_prone': error_prone,
        'review_advice': review_advice,
        'question_count': question_count,
        'provider': 'mock',
        'is_mock': True,
    }


def generate_combined_advice(student_name, scores_data, paper_key_points, paper_title):
    """
    结合成绩和试卷考点生成个性化复习建议。
    """
    if not scores_data:
        return {
            'weak_points': ['暂无成绩数据，无法判断薄弱知识点。'],
            'targeted_advice': ['请先录入成绩数据。'],
            'study_plan': {'short': '待数据补充后再制定。', 'medium': ''},
            'improvement_direction': '待分析。',
            'provider': 'mock',
            'is_mock': True,
        }

    avg = sum(s.get('score', 0) for s in scores_data) / len(scores_data)
    sorted_scores = sorted(scores_data, key=lambda x: x.get('score', 0))

    # 解析考点
    if isinstance(paper_key_points, str):
        try:
            key_points = json.loads(paper_key_points)
        except json.JSONDecodeError:
            key_points = []
    else:
        key_points = paper_key_points or []

    point_names = []
    if isinstance(key_points, list):
        for kp in key_points:
            if isinstance(kp, dict):
                point_names.append(kp.get('name', ''))
            elif isinstance(kp, str):
                point_names.append(kp)

    # 薄弱知识点
    weak_points = []
    for s in sorted_scores[:2]:
        if s.get('score', 0) < 70:
            weak_points.append(f"{s['course_name']}相关知识（当前{s['score']}分）")
    if point_names:
        weak_points.extend([f"{p}（试卷考点）" for p in point_names[:2]])
    if not weak_points:
        weak_points = ['整体基础较好，需关注细节知识点。']

    # 针对性建议
    targeted_advice = []
    for s in sorted_scores[:2]:
        if s.get('score', 0) < 60:
            targeted_advice.append(f"{s['course_name']}: 从基础概念入手，每天复习30分钟。")
        elif s.get('score', 0) < 80:
            targeted_advice.append(f"{s['course_name']}: 针对错题进行专项练习，巩固薄弱环节。")
    if point_names:
        targeted_advice.append(f"试卷重点考点（{'、'.join(point_names[:3])}）需要重点复习。")
    if not targeted_advice:
        targeted_advice.append('保持当前学习节奏，适当拓展高难度内容。')

    # 分阶段计划
    if avg < 60:
        short = "第1周: 梳理基础概念，完成课后习题。每天每科30分钟基础练习。"
        medium = "第2-4周: 系统复习各科重点，每周完成一套模拟题，查漏补缺。"
    elif avg < 80:
        short = "第1周: 整理错题本，针对薄弱知识点进行专项练习。"
        medium = "第2-4周: 提升综合应用能力，尝试中等难度题目，每周总结学习心得。"
    else:
        short = "第1周: 回顾试卷考点，挑战高难度题目。"
        medium = "第2-4周: 拓展学习广度，参加学科竞赛或深入学习。"

    # 提升方向
    worst = sorted_scores[0]
    if avg < 60:
        direction = f"优先提升{worst['course_name']}至及格线以上，同时保持其他科目不退步。"
    elif avg < 80:
        direction = f"将{worst['course_name']}提升10-15分，冲击良好等级。"
    else:
        direction = "向优秀率冲刺，争取各科均达到90分以上。"

    return {
        'weak_points': weak_points,
        'targeted_advice': targeted_advice,
        'study_plan': {'short': short, 'medium': medium},
        'improvement_direction': direction,
        'provider': 'mock',
        'is_mock': True,
    }


def _build_result(strengths, weaknesses, advice, focus, encouragement):
    """构建标准返回格式"""
    return {
        'strengths': strengths,
        'weaknesses': weaknesses,
        'advice': advice if isinstance(advice, list) else [advice],
        'focus': focus,
        'encouragement': encouragement,
        'provider': 'mock',
        'is_mock': True,
    }
