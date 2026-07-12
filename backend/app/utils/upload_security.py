"""Shared upload validation and bounded in-process rate limiting."""
import threading
import time
from collections import defaultdict, deque

from app.utils.errors import BusinessError, ErrorCode


_RATE_BUCKETS = defaultdict(deque)
_RATE_LOCK = threading.Lock()


def check_upload_rate_limit(actor_id, scope, limit=10, window_seconds=60):
    """Limit accidental/repeated uploads per worker without storing sensitive data."""
    now = time.monotonic()
    key = (str(actor_id or 'anonymous'), str(scope))
    with _RATE_LOCK:
        bucket = _RATE_BUCKETS[key]
        cutoff = now - window_seconds
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            raise BusinessError(
                ErrorCode.UPLOAD_RATE_LIMITED,
                '上传过于频繁，请稍后再试',
                http_status=429,
            )
        bucket.append(now)


def validate_xlsx_upload(file_storage, max_size_mb=10):
    """Validate an XLSX upload by extension, MIME, size, and ZIP signature."""
    if not file_storage:
        raise BusinessError(ErrorCode.UPLOAD_INVALID, '请上传 Excel 文件')

    filename = str(file_storage.filename or '')
    if not filename.lower().endswith('.xlsx'):
        raise BusinessError(ErrorCode.UPLOAD_INVALID, '仅支持 .xlsx 文件')

    allowed_mimes = {
        '',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/octet-stream',
        'application/zip',
    }
    mimetype = str(file_storage.mimetype or '').lower()
    if mimetype not in allowed_mimes:
        raise BusinessError(ErrorCode.UPLOAD_INVALID, 'Excel MIME 类型不支持')

    stream = file_storage.stream
    original_pos = stream.tell()
    stream.seek(0, 2)
    size = stream.tell()
    stream.seek(0)
    signature = stream.read(4)
    stream.seek(original_pos)

    if size <= 0:
        raise BusinessError(ErrorCode.UPLOAD_INVALID, 'Excel 文件为空')
    if size > max_size_mb * 1024 * 1024:
        raise BusinessError(ErrorCode.UPLOAD_INVALID, f'Excel 文件大小不能超过 {max_size_mb}MB')
    if signature[:2] != b'PK':
        raise BusinessError(ErrorCode.UPLOAD_INVALID, '文件内容不是有效的 .xlsx 文件')

    return {'size': size, 'mimetype': mimetype, 'extension': 'xlsx'}

