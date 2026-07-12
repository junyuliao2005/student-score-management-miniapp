import io
import json
import os
import time

import pytest
from werkzeug.datastructures import FileStorage

from app.services import ocr_service
from app.utils.errors import BusinessError, ErrorCode


def _fake_image():
    return FileStorage(io.BytesIO(b'fake-image-bytes'), filename='exam.png', content_type='image/png')


def _patch_image_pipeline(monkeypatch):
    monkeypatch.setattr(ocr_service, 'validate_image_file', lambda *args, **kwargs: {
        'size': 16, 'width': 100, 'height': 60,
    })
    monkeypatch.setattr(ocr_service, '_normalize_image', lambda value: (
        b'normalized', {'width': 100, 'height': 60, 'format': 'jpeg'},
    ))


def test_ocr_preview_owner_and_expiry(app, monkeypatch):
    _patch_image_pipeline(monkeypatch)
    with app.app_context():
        preview = ocr_service.preview_image(_fake_image(), 'T001', 'test')
        path = ocr_service._preview_path(preview['ocr_id'])
        with pytest.raises(BusinessError) as denied:
            ocr_service._load_preview(preview['ocr_id'], 'T002')
        assert denied.value.code == ErrorCode.PERMISSION_DENIED

        data = json.loads(open(path, encoding='utf-8').read())
        data['created_at'] = int(time.time()) - 1900
        with open(path, 'w', encoding='utf-8') as handle:
            json.dump(data, handle)
        with pytest.raises(BusinessError):
            ocr_service._load_preview(preview['ocr_id'], 'T001')
        assert not os.path.exists(path)


def test_ocr_confirmation_failure_cleans_preview(app, monkeypatch):
    _patch_image_pipeline(monkeypatch)
    with app.app_context():
        preview = ocr_service.preview_image(_fake_image(), 'T001', 'test')
        path = ocr_service._preview_path(preview['ocr_id'])

        def fail_analysis(**kwargs):
            raise BusinessError(ErrorCode.AI_ANALYSIS_FAILED, 'forced failure')

        monkeypatch.setattr(ocr_service.exam_analyzer, 'analyze_paper', fail_analysis)
        with pytest.raises(BusinessError):
            ocr_service.analyze_confirmed(
                preview['ocr_id'], '测试卷', '数学', '期中', '可编辑 OCR 文字', 'T001', 'test',
            )
        assert not os.path.exists(path)
