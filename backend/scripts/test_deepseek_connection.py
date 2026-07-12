"""Run one bounded DeepSeek connectivity smoke test when a key is configured."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.services.ai_provider import DeepSeekProvider, ProviderCallError


def main():
    app = create_app()
    with app.app_context():
        if not app.config.get('DEEPSEEK_API_KEY'):
            print('SKIPPED: DEEPSEEK_API_KEY is not configured')
            return 0
        provider = DeepSeekProvider(app.config)
        try:
            result_text, duration_ms, usage = provider.call(
                '返回 JSON: {"status":"ok"}',
                '只返回一个 JSON 对象，不要输出推理过程。',
            )
        except ProviderCallError as exc:
            print(f'FAIL: DeepSeek connection category={exc.category} status={exc.status_code}')
            return 1
        result = json.loads(result_text)
        print('PASS: DeepSeek connection')
        print('model:', provider.model)
        print('duration_ms:', duration_ms)
        print('usage_total_tokens:', usage.get('total_tokens'))
        print('response_status:', result.get('status', 'unknown'))
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
