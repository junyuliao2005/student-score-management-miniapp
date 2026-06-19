"""上传文件校验工具。"""
from app.utils.errors import BusinessError, ErrorCode


def validate_image_file(file_storage, allowed_exts=None, allowed_mimes=None, max_size_mb=10):
    """校验图片上传文件，返回文件元信息。"""
    allowed_exts = allowed_exts or {'jpg', 'jpeg', 'png', 'webp'}
    allowed_mimes = allowed_mimes or {'image/jpeg', 'image/png', 'image/webp'}

    if not file_storage:
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, '请上传图片文件')

    filename = file_storage.filename or ''
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in allowed_exts:
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, '仅支持 jpg、jpeg、png、webp 图片')

    mimetype = (file_storage.mimetype or '').lower()
    if mimetype and mimetype not in allowed_mimes:
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, '图片 MIME 类型不支持')

    stream = file_storage.stream
    current_pos = stream.tell()
    stream.seek(0, 2)
    size = stream.tell()
    stream.seek(current_pos)

    max_bytes = max_size_mb * 1024 * 1024
    if size <= 0:
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, '图片文件为空')
    if size > max_bytes:
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, f'图片大小不能超过 {max_size_mb}MB')

    return {
        'filename': filename,
        'extension': ext,
        'mimetype': mimetype,
        'size': size,
    }
