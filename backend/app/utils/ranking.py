"""竞赛排名算法：同分同名次，下一名跳过"""


def competition_rank(items, score_key='total_score'):
    """
    竞赛排名法。
    - 按 score_key 降序排列
    - 同分同名次
    - 下一名跳过相应位次
    示例: 100, 100, 95, 90 -> rank 1, 1, 3, 4

    参数:
        items: list[dict]，每个元素是一个字典
        score_key: str，分数字段名

    返回:
        items: 原列表（已原地修改，每个元素增加 rank_no）
    """
    if not items:
        return items

    # 过滤掉分数为 None 的记录，排在最后
    scored = [i for i in items if i.get(score_key) is not None]
    no_score = [i for i in items if i.get(score_key) is None]

    # 按分数降序
    scored.sort(key=lambda x: float(x.get(score_key, 0)), reverse=True)

    # 分配排名
    rank = 1
    idx = 0
    while idx < len(scored):
        current_score = float(scored[idx].get(score_key, 0))

        # 找出所有同分的记录
        same_count = 0
        while idx + same_count < len(scored) and \
                float(scored[idx + same_count].get(score_key, 0)) == current_score:
            scored[idx + same_count]['rank_no'] = rank
            same_count += 1

        rank += same_count
        idx += same_count

    # 没有分数的不排名
    for item in no_score:
        item['rank_no'] = None

    return scored + no_score
