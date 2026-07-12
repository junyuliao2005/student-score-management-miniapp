"""Private runtime JSON storage for short-lived server-side previews."""
import json
import os
import re
import tempfile
import time
import uuid

from flask import current_app

from app.utils.errors import BusinessError


def save_preview(kind, preview_id, data, config_key, error_code):
    path = preview_path(kind, preview_id, config_key, error_code)
    _cleanup_expired(kind, config_key)
    temp_path = f'{path}.tmp-{uuid.uuid4().hex}'
    try:
        with open(temp_path, 'x', encoding='utf-8') as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


def load_preview(kind, preview_id, owner_id, config_key, error_code, missing_message):
    path = preview_path(kind, preview_id, config_key, error_code)
    if not os.path.exists(path):
        raise BusinessError(error_code, missing_message)
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
    except (OSError, ValueError) as exc:
        raise BusinessError(error_code, missing_message) from exc
    if data.get('operator_id') != owner_id:
        raise BusinessError(error_code, '无权使用该导入预览')
    ttl = int(current_app.config.get('IMPORT_PREVIEW_TTL_SECONDS', 1800))
    if int(time.time()) - int(data.get('created_at') or 0) > ttl:
        delete_preview(kind, preview_id, config_key, error_code)
        raise BusinessError(error_code, missing_message)
    return data


def delete_preview(kind, preview_id, config_key, error_code):
    path = preview_path(kind, preview_id, config_key, error_code)
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        return False
    return True


def preview_path(kind, preview_id, config_key, error_code):
    value = str(preview_id or '')
    if not re.fullmatch(r'[0-9a-f]{32}', value):
        raise BusinessError(error_code, '导入预览标识无效')
    return os.path.join(resolve_private_dir(config_key, kind), f'{value}.json')


def resolve_private_dir(config_key, subdir):
    cache_key = f'private_runtime_dir:{config_key}:{subdir}'
    cached = current_app.extensions.get(cache_key)
    if cached:
        return cached

    configured = str(current_app.config.get(config_key) or '').strip()
    backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    candidates = [configured] if configured else []
    candidates.extend([
        os.path.join(backend_root, '.runtime', subdir),
        os.path.join(tempfile.gettempdir(), 'student_grade_backend', subdir),
    ])
    for path in candidates:
        try:
            os.makedirs(path, exist_ok=True)
            if os.name != 'nt':
                os.chmod(path, 0o700)
            probe = os.path.join(path, f'.probe-{uuid.uuid4().hex}')
            with open(probe, 'x', encoding='ascii') as handle:
                handle.write('ok')
            os.remove(probe)
            current_app.extensions[cache_key] = path
            return path
        except OSError:
            continue
    raise BusinessError(error_code, '导入预览缓存目录不可写，请检查服务运行权限')


def _cleanup_expired(kind, config_key):
    directory = resolve_private_dir(config_key, kind)
    ttl = int(current_app.config.get('IMPORT_PREVIEW_TTL_SECONDS', 1800))
    cutoff = time.time() - ttl
    try:
        for name in os.listdir(directory):
            if not re.fullmatch(r'[0-9a-f]{32}\.json', name):
                continue
            path = os.path.join(directory, name)
            if os.path.getmtime(path) < cutoff:
                os.remove(path)
    except OSError:
        return
