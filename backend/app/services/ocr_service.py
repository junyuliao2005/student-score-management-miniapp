"""Secure OCR preview -> user correction -> confirmed AI analysis workflow."""
import io
import json
import logging
import os
import re
import tempfile
import time
import uuid

from flask import current_app

from app.services import audit_service, exam_analyzer
from app.services.ocr_provider import LocalOCRProvider, MockOCRProvider, OCRUnavailableError
from app.utils.errors import BusinessError, ErrorCode
from app.utils.file_validator import validate_image_file
from app.utils.privacy_sanitizer import mask_sensitive_text
from app.utils.text_sanitizer import sanitize_input

logger = logging.getLogger(__name__)


def preview_image(image_file, operator_id, trace_id=''):
    info = validate_image_file(
        image_file,
        max_size_mb=current_app.config.get('AI_VISION_MAX_IMAGE_MB', 10),
        max_pixels=current_app.config.get('OCR_MAX_PIXELS', 24_000_000),
        max_dimension=current_app.config.get('OCR_MAX_DIMENSION', 10_000),
    )
    image_file.stream.seek(0)
    normalized_bytes, image_meta = _normalize_image(image_file.stream.read())

    provider_name = str(current_app.config.get('OCR_PROVIDER', 'mock')).lower()
    fallback_enabled = bool(current_app.config.get('OCR_FALLBACK_ENABLED', True))
    provider = LocalOCRProvider() if provider_name == 'local' else MockOCRProvider()
    try:
        result = provider.recognize(normalized_bytes)
    except OCRUnavailableError as exc:
        if not fallback_enabled:
            raise BusinessError(ErrorCode.AI_ANALYSIS_FAILED, str(exc)) from exc
        result = MockOCRProvider().recognize(normalized_bytes)
        result['mode'] = 'fallback'
        result['warnings'].insert(0, str(exc))

    result['raw_text'] = mask_sensitive_text(result.get('raw_text'))
    result['normalized_text'] = mask_sensitive_text(result.get('normalized_text'))
    ocr_id = uuid.uuid4().hex
    cache = {
        'ocr_id': ocr_id,
        'operator_id': operator_id,
        'created_at': int(time.time()),
        'raw_text': result['raw_text'][:10000],
        'normalized_text': result['normalized_text'][:10000],
        'confidence': result.get('confidence'),
        'provider': result.get('provider'),
        'mode': result.get('mode'),
        'warnings': result.get('warnings') or [],
    }
    _save_preview(ocr_id, cache)
    audit_service.write(
        action='ocr.preview',
        operator_id=operator_id,
        target_type='ocr_preview',
        target_id=ocr_id,
        detail={
            'provider': cache['provider'],
            'mode': cache['mode'],
            'image_size': info['size'],
            'width': image_meta['width'],
            'height': image_meta['height'],
        },
        trace_id=trace_id,
    )
    from app.extensions import db
    db.session.commit()
    return {
        **cache,
        'image': image_meta,
    }


def analyze_confirmed(ocr_id, title, subject, exam_batch, corrected_text, operator_id, trace_id=''):
    preview = _load_preview(ocr_id, operator_id)
    source_text = corrected_text if corrected_text is not None else preview.get('normalized_text')
    cleaned_text, warnings = sanitize_input(mask_sensitive_text(source_text), max_chars=10000)
    if not cleaned_text:
        raise BusinessError(ErrorCode.AI_ANALYSIS_FAILED, 'OCR 文字为空，请先修改识别文字再确认分析')
    try:
        result = exam_analyzer.analyze_paper(
            title=title,
            subject=subject,
            exam_batch=exam_batch,
            paper_text=cleaned_text,
            operator_id=operator_id,
            trace_id=trace_id,
        )
        result['ocr'] = {
            'ocr_id': ocr_id,
            'provider': preview.get('provider'),
            'mode': preview.get('mode'),
            'confidence': preview.get('confidence'),
            'warnings': (preview.get('warnings') or []) + warnings,
        }
        audit_service.write(
            action='ocr.confirm_analyze',
            operator_id=operator_id,
            target_type='exam_paper',
            target_id=result.get('paper_id'),
            detail={'ocr_id': ocr_id, 'ocr_provider': preview.get('provider')},
            trace_id=trace_id,
        )
        from app.extensions import db
        db.session.commit()
        return result
    finally:
        _delete_preview(ocr_id)


def _normalize_image(image_bytes):
    try:
        from PIL import Image, ImageOps
        with Image.open(io.BytesIO(image_bytes)) as source:
            image = ImageOps.exif_transpose(source).convert('RGB')
            max_side = int(current_app.config.get('OCR_NORMALIZE_MAX_SIDE', 3000))
            if max(image.size) > max_side:
                image.thumbnail((max_side, max_side))
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=88, optimize=True)
            return output.getvalue(), {
                'width': image.width,
                'height': image.height,
                'format': 'jpeg',
            }
    except Exception as exc:
        raise BusinessError(ErrorCode.UPLOAD_INVALID, '图片解码或规范化失败') from exc


def _preview_dir():
    cached = current_app.extensions.get('ocr_preview_dir')
    if cached:
        return cached
    configured = str(current_app.config.get('OCR_PREVIEW_DIR') or '').strip()
    backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    candidates = [configured] if configured else []
    candidates.extend([
        os.path.join(backend_root, '.tmp', 'ocr_previews'),
        os.path.join(backend_root, '.runtime', 'ocr-previews'),
        os.path.join(tempfile.gettempdir(), 'student_grade_backend', 'ocr_previews'),
    ])
    for path in candidates:
        try:
            os.makedirs(path, exist_ok=True)
            if os.name != 'nt':
                os.chmod(path, 0o700)
            probe_path = os.path.join(path, f'.write_probe_{uuid.uuid4().hex}')
            with open(probe_path, 'xb') as probe:
                probe.write(b'ok')
            os.remove(probe_path)
            current_app.extensions['ocr_preview_dir'] = path
            return path
        except OSError as exc:
            logger.warning('OCR preview directory is not writable: %s (%s)', path, exc)
    raise BusinessError(ErrorCode.AI_ANALYSIS_FAILED, 'OCR 临时缓存目录不可写，请检查服务运行权限')


def _preview_path(ocr_id):
    safe_id = str(ocr_id or '')
    if not re.fullmatch(r'[0-9a-f]{32}', safe_id):
        raise BusinessError(ErrorCode.AI_ANALYSIS_FAILED, 'OCR 预览标识无效')
    return os.path.join(_preview_dir(), f'{safe_id}.json')


def _save_preview(ocr_id, data):
    _cleanup_expired()
    with open(_preview_path(ocr_id), 'w', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False)


def _load_preview(ocr_id, operator_id):
    path = _preview_path(ocr_id)
    if not ocr_id or not os.path.exists(path):
        raise BusinessError(ErrorCode.AI_ANALYSIS_FAILED, 'OCR 预览不存在或已过期')
    with open(path, 'r', encoding='utf-8') as handle:
        data = json.load(handle)
    if data.get('operator_id') != operator_id:
        raise BusinessError(ErrorCode.PERMISSION_DENIED, '无权使用该 OCR 预览')
    if int(time.time()) - int(data.get('created_at') or 0) > 1800:
        _delete_preview(ocr_id)
        raise BusinessError(ErrorCode.AI_ANALYSIS_FAILED, 'OCR 预览已过期，请重新上传')
    return data


def _delete_preview(ocr_id):
    try:
        path = _preview_path(ocr_id)
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        logger.warning('OCR preview cleanup failed: ocr_id=%s', ocr_id)


def _cleanup_expired():
    now = time.time()
    try:
        for name in os.listdir(_preview_dir()):
            path = os.path.join(_preview_dir(), name)
            if os.path.isfile(path) and now - os.path.getmtime(path) > 1800:
                os.remove(path)
    except OSError:
        logger.warning('Expired OCR preview cleanup failed')
