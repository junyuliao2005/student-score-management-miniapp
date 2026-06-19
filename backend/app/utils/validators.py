"""参数校验工具"""
from app.utils.errors import BusinessError, ErrorCode


def require_fields(data, fields):
    """校验必填字段，缺失时抛 BusinessError"""
    if not data:
        raise BusinessError(ErrorCode.LOGIN_REQUIRED, '请求体不能为空')
    missing = [f for f in fields if f not in data or data[f] is None or data[f] == '']
    if missing:
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, f'缺少必填字段: {", ".join(missing)}')


def validate_pagination(args):
    """校验并返回分页参数"""
    try:
        page = int(args.get('page', 1))
        page_size = int(args.get('page_size', 20))
    except (ValueError, TypeError):
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, '分页参数必须为整数')
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20
    if page_size > 100:
        page_size = 100
    return page, page_size


def validate_score_range(score):
    """校验分数范围 0-100"""
    try:
        score = float(score)
    except (ValueError, TypeError):
        raise BusinessError(ErrorCode.SCORE_OUT_OF_RANGE, '分数必须为数字')
    if score < 0 or score > 100:
        raise BusinessError(ErrorCode.SCORE_OUT_OF_RANGE, '分数必须在 0 到 100 之间')
    return score
