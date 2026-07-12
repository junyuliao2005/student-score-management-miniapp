"""上传文件校验工具。"""
import io
import uuid

from app.utils.errors import BusinessError, ErrorCode


def validate_image_file(
    file_storage,
    allowed_exts=None,
    allowed_mimes=None,
    max_size_mb=10,
    max_pixels=24_000_000,
    max_dimension=10_000,
):
    """校验图片上传文件，返回文件元信息。"""
    allowed_exts = allowed_exts or {'jpg', 'jpeg', 'png', 'webp'}
    allowed_mimes = allowed_mimes or {'image/jpeg', 'image/png', 'image/webp'}

    if not file_storage:
        raise BusinessError(ErrorCode.UPLOAD_INVALID, '请上传图片文件')

    filename = file_storage.filename or ''
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in allowed_exts:
        raise BusinessError(ErrorCode.UPLOAD_INVALID, '仅支持 jpg、jpeg、png、webp 图片')

    mimetype = (file_storage.mimetype or '').lower()
    if mimetype and mimetype not in allowed_mimes:
        raise BusinessError(ErrorCode.UPLOAD_INVALID, '图片 MIME 类型不支持')

    stream = file_storage.stream
    current_pos = stream.tell()
    stream.seek(0, 2)
    size = stream.tell()
    stream.seek(current_pos)

    max_bytes = max_size_mb * 1024 * 1024
    if size <= 0:
        raise BusinessError(ErrorCode.UPLOAD_INVALID, '图片文件为空')
    if size > max_bytes:
        raise BusinessError(ErrorCode.UPLOAD_INVALID, f'图片大小不能超过 {max_size_mb}MB')

    stream.seek(0)
    image_bytes = stream.read()
    stream.seek(current_pos)

    try:
        from PIL import Image
        with Image.open(io.BytesIO(image_bytes)) as image:
            detected_format = str(image.format or '').lower()
            width, height = image.size
            image.verify()
    except Exception as exc:
        raise BusinessError(ErrorCode.UPLOAD_INVALID, '图片内容损坏或格式不受支持') from exc

    format_to_ext = {'jpeg': {'jpg', 'jpeg'}, 'png': {'png'}, 'webp': {'webp'}}
    if detected_format not in format_to_ext or ext not in format_to_ext[detected_format]:
        raise BusinessError(ErrorCode.UPLOAD_INVALID, '图片扩展名与实际内容不一致')
    if width <= 0 or height <= 0 or width > max_dimension or height > max_dimension:
        raise BusinessError(ErrorCode.UPLOAD_INVALID, '图片尺寸不符合要求')
    if width * height > max_pixels:
        raise BusinessError(ErrorCode.UPLOAD_INVALID, '图片像素过大，请压缩后重试')

    safe_filename = f'{uuid.uuid4().hex}.{ext}'
    return {
        'filename': safe_filename,
        'extension': ext,
        'mimetype': mimetype,
        'size': size,
        'width': width,
        'height': height,
        'detected_format': detected_format,
    }
