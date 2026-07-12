"""OCR provider abstraction. Local OCR is optional and isolated from core startup."""
import logging

logger = logging.getLogger(__name__)


class OCRUnavailableError(RuntimeError):
    pass


class LocalOCRProvider:
    name = 'rapidocr'

    def recognize(self, image_bytes):
        try:
            from rapidocr import RapidOCR
        except ImportError as exc:
            raise OCRUnavailableError('RapidOCR 未安装') from exc

        try:
            engine = RapidOCR()
            output = engine(image_bytes)
            texts, scores = _extract_output(output)
        except Exception as exc:
            logger.warning('Local OCR failed: type=%s', type(exc).__name__)
            raise OCRUnavailableError('本地 OCR 识别失败') from exc

        raw_text = '\n'.join(text for text in texts if text)
        confidence = round(sum(scores) / len(scores), 4) if scores else None
        warnings = [] if raw_text else ['未识别出文字，请检查图片清晰度或手动输入']
        return {
            'raw_text': raw_text,
            'normalized_text': _normalize_text(raw_text),
            'confidence': confidence,
            'provider': self.name,
            'mode': 'real',
            'warnings': warnings,
        }


class MockOCRProvider:
    name = 'mock_ocr'

    def recognize(self, image_bytes):
        return {
            'raw_text': '',
            'normalized_text': '',
            'confidence': None,
            'provider': self.name,
            'mode': 'mock',
            'warnings': ['当前环境未启用本地 OCR，请在预览框中手动录入或粘贴试卷文字后确认分析'],
        }


def _extract_output(output):
    texts = []
    scores = []
    if hasattr(output, 'txts'):
        texts = list(output.txts or [])
        scores = [float(v) for v in (getattr(output, 'scores', None) or [])]
        return texts, scores
    if isinstance(output, tuple) and output:
        output = output[0]
    for item in output or []:
        if isinstance(item, (list, tuple)) and len(item) >= 3:
            texts.append(str(item[1] or ''))
            try:
                scores.append(float(item[2]))
            except (TypeError, ValueError):
                pass
    return texts, scores


def _normalize_text(text):
    lines = [' '.join(str(line).split()) for line in str(text or '').splitlines()]
    return '\n'.join(line for line in lines if line).strip()

