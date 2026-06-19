"""统一业务异常定义"""


class BusinessError(Exception):
    """业务异常，携带统一错误码"""

    def __init__(self, code, message, data=None, http_status=None):
        self.code = code
        self.message = message
        self.data = data
        self.http_status = http_status or _code_to_http_status(code)
        super().__init__(message)


def _code_to_http_status(code):
    """业务错误码 -> HTTP 状态码映射"""
    if code == 0:
        return 200
    if 20001 <= code <= 20007:
        return 400
    if 30001 <= code <= 30002:
        return 403
    if 40001 <= code <= 40003:
        return 401
    if 50001 <= code <= 50003:
        return 500
    if 60001 <= code <= 60003:
        return 500
    return 500


# 预定义错误码常量
class ErrorCode:
    SUCCESS = 0
    SCORE_OUT_OF_RANGE = 20001
    SCORE_DUPLICATE = 20002
    COURSE_NOT_FOUND = 20003
    STUDENT_NOT_FOUND = 20004
    CONFIG_MISSING = 20005
    SCORE_IMPORT_INVALID = 20006
    USER_IMPORT_INVALID = 20007
    PERMISSION_DENIED = 30001
    ROLE_MAPPING_INVALID = 30002
    TOKEN_EXPIRED = 40001
    TOKEN_INVALID = 40002
    LOGIN_REQUIRED = 40003
    DB_TRANSACTION_FAILED = 50001
    STAT_REFRESH_FAILED = 50002
    INTERNAL_SERVER_ERROR = 50003
    AI_ANALYSIS_FAILED = 60001
    AI_INPUT_TOO_LONG = 60002
    AI_RATE_LIMITED = 60003
