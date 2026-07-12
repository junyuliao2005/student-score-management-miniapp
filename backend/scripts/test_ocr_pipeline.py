"""Offline OCR preview/confirm pipeline test. Never calls a paid AI API."""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from PIL import Image
except ImportError:
    print('SKIPPED: Pillow is not installed; install requirements.txt or use the OCR environment')
    raise SystemExit(0)

from werkzeug.datastructures import FileStorage

from app import create_app
from app.extensions import db
from app.services import ocr_service
from config import TestConfig


class OCRTestConfig(TestConfig):
    OCR_PROVIDER = 'mock'
    OCR_FALLBACK_ENABLED = True
    AI_PROVIDER = 'mock'
    AI_FALLBACK_ENABLED = True


def main():
    app = create_app(OCRTestConfig)
    with app.app_context():
        db.create_all()
        image_buffer = io.BytesIO()
        Image.new('RGB', (320, 180), color='white').save(image_buffer, format='PNG')
        image_buffer.seek(0)
        upload = FileStorage(image_buffer, filename='exam.png', content_type='image/png')

        preview = ocr_service.preview_image(upload, operator_id='T001', trace_id='ocr-test')
        assert preview['ocr_id']
        assert preview['provider'] == 'mock_ocr'
        preview_path = ocr_service._preview_path(preview['ocr_id'])
        assert os.path.exists(preview_path)

        result = ocr_service.analyze_confirmed(
            ocr_id=preview['ocr_id'],
            title='数学单元测试',
            subject='数学',
            exam_batch='单元测试',
            corrected_text='1. 计算一元一次方程。\n2. 解答几何应用题。',
            operator_id='T001',
            trace_id='ocr-test',
        )
        assert result['paper_id']
        assert result['mode'] == 'mock'
        assert not os.path.exists(preview_path)
        print('PASS: OCR preview -> correction -> mock AI analysis -> cleanup')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

