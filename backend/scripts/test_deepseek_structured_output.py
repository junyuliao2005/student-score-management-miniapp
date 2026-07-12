"""Run one minimal structured-output smoke test when DeepSeek is configured."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.services.ai_provider import DeepSeekProvider, ProviderCallError
from app.services.ai_result_schema import normalize_ai_result


def main():
    app = create_app()
    with app.app_context():
        if not app.config.get('DEEPSEEK_API_KEY'):
            print('SKIPPED: DEEPSEEK_API_KEY is not configured')
            return 0
        provider = DeepSeekProvider(app.config)
        try:
            result_text, duration_ms, usage = provider.call(
                '根据数学 82 分生成简短建议，返回 strengths、weaknesses、advice、focus、encouragement。',
                '只返回 JSON 对象；advice 必须是字符串数组；不要输出推理过程。',
            )
        except ProviderCallError as exc:
            print(f'FAIL: DeepSeek structured output category={exc.category} status={exc.status_code}')
            return 1
        normalized = normalize_ai_result('student_advice', json.loads(result_text))
        required = ('strengths', 'weaknesses', 'advice', 'focus', 'encouragement')
        if not all(key in normalized for key in required):
            raise RuntimeError('structured output validation failed')
        print('PASS: DeepSeek structured output')
        print('model:', provider.model)
        print('duration_ms:', duration_ms)
        print('usage_total_tokens:', usage.get('total_tokens'))
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
