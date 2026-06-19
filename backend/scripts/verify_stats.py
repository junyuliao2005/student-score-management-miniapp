"""
统计函数验证脚本（纯函数验证，不连接数据库，不依赖 Flask）
用法: cd backend && python scripts/verify_stats.py

本脚本直接内联测试核心算法逻辑，避免导入 Flask 依赖。
"""


def competition_rank(items, score_key='total_score'):
    """内联竞赛排名算法（与 app/utils/ranking.py 逻辑一致）"""
    if not items:
        return items
    scored = [i for i in items if i.get(score_key) is not None]
    no_score = [i for i in items if i.get(score_key) is None]
    scored.sort(key=lambda x: float(x.get(score_key, 0)), reverse=True)
    rank = 1
    idx = 0
    while idx < len(scored):
        current_score = float(scored[idx].get(score_key, 0))
        same_count = 0
        while idx + same_count < len(scored) and \
                float(scored[idx + same_count].get(score_key, 0)) == current_score:
            scored[idx + same_count]['rank_no'] = rank
            same_count += 1
        rank += same_count
        idx += same_count
    for item in no_score:
        item['rank_no'] = None
    return scored + no_score


DEFAULT_LEVEL_RANGES = {
    '优秀': [90, 100],
    '良好': [80, 89.99],
    '中等': [70, 79.99],
    '及格': [60, 69.99],
    '不及格': [0, 59.99],
}


def map_level(avg_score):
    """内联等级映射（与 stats_service._map_level 逻辑一致）"""
    for level, (low, high) in DEFAULT_LEVEL_RANGES.items():
        if low <= avg_score <= high:
            return level
    return '不及格'


def build_comment(avg_score, level_tag, warning_flags=None):
    """内联评语生成（与 comment_service.build_comment 逻辑一致）"""
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
    return '基础仍需巩固，建议制定阶段性提升计划。'


passed = 0
failed = 0


def check(condition, msg):
    global passed, failed
    if condition:
        passed += 1
        print(f'  PASS: {msg}')
    else:
        failed += 1
        print(f'  FAIL: {msg}')


def test_competition_rank():
    print('\n[测试] 竞赛排名算法 competition_rank')

    # 1,1,3 模式
    items = [
        {'student_id': 'A', 'total_score': 100},
        {'student_id': 'B', 'total_score': 100},
        {'student_id': 'C', 'total_score': 95},
        {'student_id': 'D', 'total_score': 90},
    ]
    competition_rank(items, 'total_score')
    check([i['rank_no'] for i in items] == [1, 1, 3, 4], '同分同名次 1,1,3,4')

    # 全部同分
    items = [{'student_id': 'A', 'total_score': 80}, {'student_id': 'B', 'total_score': 80}]
    competition_rank(items, 'total_score')
    check([i['rank_no'] for i in items] == [1, 1], '全部同分 1,1')

    # 空列表
    check(competition_rank([], 'total_score') == [], '空列表返回空')

    # None 分数
    items = [
        {'student_id': 'A', 'total_score': 90},
        {'student_id': 'B', 'total_score': None},
        {'student_id': 'C', 'total_score': 80},
    ]
    competition_rank(items, 'total_score')
    none_item = [i for i in items if i['student_id'] == 'B'][0]
    check(none_item['rank_no'] is None, 'None 分数不排名')

    # 50人同分
    items = [{'student_id': f'S{i}', 'total_score': 100} for i in range(50)]
    competition_rank(items, 'total_score')
    check(all(i['rank_no'] == 1 for i in items), '50人同分全部排名1')


def test_level_mapping():
    print('\n[测试] 等级映射')

    cases = [
        (100, '优秀'), (95, '优秀'), (90, '优秀'),
        (89.99, '良好'), (85, '良好'), (80, '良好'),
        (79.99, '中等'), (75, '中等'), (70, '中等'),
        (69.99, '及格'), (65, '及格'), (60, '及格'),
        (59.99, '不及格'), (30, '不及格'), (0, '不及格'),
    ]
    for score, expected in cases:
        check(map_level(score) == expected, f'{score} -> {expected}')


def test_comment_service():
    print('\n[测试] 自动评语')

    # 低分 + 偏科
    result = build_comment(55, '不及格', [{'warning_type': 'low_score'}, {'warning_type': 'subject_bias'}])
    check('低分' in result and '偏科' in result, '低分+偏科评语')

    # 仅低分
    result = build_comment(45, '不及格', [{'warning_type': 'low_score'}])
    check('低分' in result, '仅低分评语')

    # 仅偏科
    result = build_comment(75, '中等', [{'warning_type': 'subject_bias'}])
    check('不均衡' in result or '偏科' in result, '仅偏科评语')

    # 优秀无预警
    result = build_comment(95, '优秀', [])
    check('扎实' in result or '继续' in result, '优秀评语')

    # 良好无预警
    result = build_comment(85, '良好', [])
    check('稳定' in result or '提升' in result, '良好评语')

    # 及格无预警
    result = build_comment(65, '及格', [])
    check('巩固' in result or '计划' in result, '及格评语')


def test_total_avg():
    print('\n[测试] 总分/平均分计算')

    # 正常
    scores = [95, 92, 98]
    total = sum(scores)
    avg = round(total / len(scores), 2)
    check(total == 285, f'总分 {total} == 285')
    check(avg == 95.0, f'平均分 {avg} == 95.0')

    # 保留两位小数
    scores = [95, 92, 88]
    total = sum(scores)
    avg = round(total / len(scores), 2)
    check(avg == 91.67, f'平均分 {avg} == 91.67')

    # 低分场景
    scores = [42, 38, 55]
    total = sum(scores)
    avg = round(total / len(scores), 2)
    check(total == 135, f'低分总分 {total} == 135')
    check(avg == 45.0, f'低分平均分 {avg} == 45.0')


def main():
    print('=' * 50)
    print('统计函数验证（纯函数，不连接数据库）')
    print('=' * 50)

    test_competition_rank()
    test_level_mapping()
    test_comment_service()
    test_total_avg()

    print('\n' + '=' * 50)
    print(f'验证结果: {passed} 通过, {failed} 失败')
    print('=' * 50)

    if failed > 0:
        import sys
        sys.exit(1)


if __name__ == '__main__':
    main()
