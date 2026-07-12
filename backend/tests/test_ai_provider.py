import json

import pytest
import requests

from app.services import ai_provider
from app.services.ai_provider import DeepSeekProvider, ProviderCallError


class FakeResponse:
    def __init__(self, status_code=200, body=None):
        self.status_code = status_code
        self._body = body or {}

    def json(self):
        return self._body


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def _config():
    return {
        'DEEPSEEK_API_KEY': 'test-key',
        'DEEPSEEK_BASE_URL': 'https://api.deepseek.example',
        'DEEPSEEK_CHAT_ENDPOINT': '/chat/completions',
        'DEEPSEEK_MODEL': 'deepseek-v4-pro',
        'AI_TIMEOUT_SECONDS': 5,
        'AI_MAX_RETRIES': 0,
    }


def test_deepseek_uses_chat_completions_and_final_content_only():
    client = FakeClient(FakeResponse(body={
        'choices': [{
            'finish_reason': 'stop',
            'message': {'reasoning_content': 'private reasoning', 'content': '{"summary":"ok"}'},
        }],
        'usage': {'prompt_tokens': 2, 'completion_tokens': 3, 'total_tokens': 5},
    }))
    provider = DeepSeekProvider(_config(), http_client=client)
    text, _, usage = provider.call('test')
    assert json.loads(text) == {'summary': 'ok'}
    assert usage['total_tokens'] == 5
    assert client.calls[0][0].endswith('/chat/completions')
    assert '/responses' not in client.calls[0][0]
    assert 'test-key' not in json.dumps(client.calls[0][1]['json'])


def test_deepseek_401_is_explicit_and_not_retryable():
    client = FakeClient(FakeResponse(status_code=401))
    with pytest.raises(ProviderCallError) as error:
        DeepSeekProvider(_config(), http_client=client).call('test')
    assert error.value.category == 'authentication'
    assert len(client.calls) == 1


@pytest.mark.parametrize(
    ('status_code', 'category'),
    [(402, 'quota'), (429, 'rate_limit'), (500, 'server')],
)
def test_deepseek_http_errors_are_classified(status_code, category):
    client = FakeClient(FakeResponse(status_code=status_code))
    config = _config()
    config['AI_MAX_RETRIES'] = 1
    with pytest.raises(ProviderCallError) as error:
        DeepSeekProvider(config, http_client=client).call('test')
    assert error.value.category == category
    expected_calls = 2 if status_code in (429, 500) else 1
    assert len(client.calls) == expected_calls


def test_deepseek_timeout_is_bounded_and_classified():
    client = FakeClient(requests.Timeout('bounded test timeout'))
    config = _config()
    config['AI_MAX_RETRIES'] = 1
    with pytest.raises(ProviderCallError) as error:
        DeepSeekProvider(config, http_client=client).call('test')
    assert error.value.category == 'timeout'
    assert len(client.calls) == 2


def test_deepseek_failure_uses_explicit_fallback(app, monkeypatch):
    class FailingProvider:
        name = 'deepseek'
        model = 'deepseek-v4-pro'

        def call(self, prompt, system_message=None):
            raise ProviderCallError('network', 'offline test')

    with app.app_context():
        app.config.update(AI_PROVIDER='deepseek', AI_FALLBACK_ENABLED=True)
        monkeypatch.setattr(ai_provider, '_build_provider', lambda name: FailingProvider())
        assert ai_provider.call_ai_api('synthetic K12 prompt') is None
        info = ai_provider.get_mock_provider_info()
        assert info['mode'] == 'fallback'
        assert info['provider'] == 'mock'
        assert info['is_mock'] is True
        assert info['fallback_from'] == 'deepseek:deepseek-v4-pro'
