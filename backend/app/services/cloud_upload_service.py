"""Consume short-lived CloudBase URLs without trusting arbitrary client URLs."""
import io
import os
from urllib.parse import urlparse

import requests
from flask import current_app
from werkzeug.datastructures import FileStorage

from app.utils.errors import BusinessError, ErrorCode


def fetch_as_file_storage(payload, max_size_mb=10):
    temp_url = str((payload or {}).get('temp_url') or '').strip()
    file_id = str((payload or {}).get('file_id') or '').strip()
    original_name = os.path.basename(str((payload or {}).get('file_name') or 'upload.bin'))
    if not temp_url or len(temp_url) > 4096 or not file_id.startswith('cloud://'):
        raise BusinessError(ErrorCode.UPLOAD_INVALID, '云存储文件信息无效')

    parsed = urlparse(temp_url)
    try:
        port = parsed.port
    except ValueError as exc:
        raise BusinessError(ErrorCode.UPLOAD_INVALID, '云存储临时地址格式无效') from exc
    if (
        parsed.scheme != 'https'
        or parsed.username
        or parsed.password
        or port not in (None, 443)
        or not parsed.path
        or not _host_allowed(parsed.hostname)
    ):
        raise BusinessError(ErrorCode.UPLOAD_INVALID, '云存储临时地址不在允许范围内')

    max_bytes = int(max_size_mb * 1024 * 1024)
    response = None
    try:
        response = requests.get(temp_url, stream=True, timeout=(5, 20), allow_redirects=False)
        if response.status_code != 200:
            raise BusinessError(ErrorCode.UPLOAD_INVALID, '云存储临时文件不可访问')

        content_length = response.headers.get('Content-Length')
        if content_length:
            try:
                if int(content_length) > max_bytes:
                    raise BusinessError(ErrorCode.UPLOAD_INVALID, f'文件大小不能超过 {max_size_mb}MB')
            except ValueError as exc:
                raise BusinessError(ErrorCode.UPLOAD_INVALID, '云存储文件长度无效') from exc

        buffer = io.BytesIO()
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            buffer.write(chunk)
            if buffer.tell() > max_bytes:
                raise BusinessError(ErrorCode.UPLOAD_INVALID, f'文件大小不能超过 {max_size_mb}MB')
        if buffer.tell() == 0:
            raise BusinessError(ErrorCode.UPLOAD_INVALID, '云存储文件为空')
        content_type = response.headers.get('Content-Type') or 'application/octet-stream'
    except requests.RequestException as exc:
        raise BusinessError(ErrorCode.UPLOAD_INVALID, '云存储文件下载失败') from exc
    finally:
        if response is not None:
            response.close()

    buffer.seek(0)
    return FileStorage(
        stream=buffer,
        filename=original_name,
        content_type=content_type,
    )


def _host_allowed(hostname):
    host = str(hostname or '').lower()
    configured = current_app.config.get('CLOUD_UPLOAD_ALLOWED_HOST_SUFFIXES') or ()
    return any(host == suffix.lstrip('.') or host.endswith(suffix) for suffix in configured)
