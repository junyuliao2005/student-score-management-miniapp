"""AI provider abstraction with explicit real/mock/fallback modes."""
import contextvars
import json
import logging
import re
import time
from datetime import datetime, timezone

import requests
from flask import current_app

from app.utils.errors import BusinessError, ErrorCode

logger = logging.getLogger(__name__)

_CALL_STATE = contextvars.ContextVar('ai_call_state', default={
    'mode': 'mock',
    'provider': 'mock',
    'model': None,
    'fallback_from': None,
})


class ProviderCallError(Exception):
    def __init__(self, category, message, retryable=False, status_code=None):
        super().__init__(message)
        self.category = category
        self.retryable = retryable
        self.status_code = status_code


class MockProvider:
    name = 'mock'
    model = None

    def info(self, mode='mock', fallback_from=None):
        return {
            'provider': self.name,
            'model': self.model,
            'mode': mode,
            'is_mock': True,
            'fallback_from': fallback_from,
        }


class DeepSeekProvider:
    name = 'deepseek'

    def __init__(self, config, http_client=requests):
        self.api_key = str(config.get('DEEPSEEK_API_KEY') or '')
        self.base_url = str(config.get('DEEPSEEK_BASE_URL') or 'https://api.deepseek.com').rstrip('/')
        endpoint = str(config.get('DEEPSEEK_CHAT_ENDPOINT') or '/chat/completions')
        self.endpoint = endpoint if endpoint.startswith('/') else f'/{endpoint}'
        self.model = str(config.get('DEEPSEEK_MODEL') or 'deepseek-v4-pro')
        self.timeout = int(config.get('AI_TIMEOUT_SECONDS', 90))
        self.max_retries = min(max(int(config.get('AI_MAX_RETRIES', 2)), 0), 2)
        self.thinking_enabled = bool(config.get('DEEPSEEK_THINKING_ENABLED', True))
        self.reasoning_effort = str(config.get('DEEPSEEK_REASONING_EFFORT') or 'max')
        self.http_client = http_client

    @property
    def url(self):
        return f'{self.base_url}{self.endpoint}'

    def call(self, prompt, system_message=None):
        if not self.api_key:
            raise ProviderCallError('configuration', 'DEEPSEEK_API_KEY 未配置')

        messages = [{
            'role': 'system',
            'content': system_message or '你是 K12 学情分析助手。只返回一个符合要求的 JSON 对象，不要输出 Markdown 或推理过程。',
        }, {
            'role': 'user',
            'content': prompt,
        }]
        payload = {
            'model': self.model,
            'messages': messages,
            'response_format': {'type': 'json_object'},
            'temperature': 0.3,
            'max_tokens': 2500,
        }
        if self.name == 'deepseek':
            payload['thinking'] = {'type': 'enabled'} if self.thinking_enabled else {'type': 'disabled'}
            payload['reasoning_effort'] = self.reasoning_effort
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }

        started = time.monotonic()
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.http_client.post(
                    self.url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )
                self._raise_for_status(response.status_code)
                data = response.json()
                choices = data.get('choices') or []
                if not choices:
                    raise ProviderCallError('invalid_response', 'DeepSeek 响应缺少 choices')
                choice = choices[0]
                finish_reason = choice.get('finish_reason')
                if finish_reason != 'stop':
                    raise ProviderCallError(
                        'incomplete_response',
                        f'DeepSeek 输出未正常结束: {finish_reason or "unknown"}',
                        retryable=finish_reason in ('length', None),
                    )
                message = choice.get('message') or {}
                # Deliberately ignore reasoning_content. Only final content is used.
                parsed = _parse_json_object(message.get('content'))
                duration_ms = int((time.monotonic() - started) * 1000)
                usage = _normalize_usage(data.get('usage'))
                return json.dumps(parsed, ensure_ascii=False), duration_ms, usage
            except requests.Timeout:
                last_error = ProviderCallError('timeout', 'DeepSeek 请求超时', retryable=True)
            except requests.RequestException:
                last_error = ProviderCallError('network', 'DeepSeek 网络请求失败', retryable=True)
            except (ValueError, TypeError, KeyError):
                last_error = ProviderCallError('invalid_response', 'DeepSeek 返回格式无效')
            except ProviderCallError as exc:
                last_error = exc

            if last_error and last_error.retryable and attempt < self.max_retries:
                time.sleep(0.5 * (2 ** attempt))
                continue
            break

        error = last_error or ProviderCallError('unknown', 'DeepSeek 调用失败')
        logger.warning(
            'DeepSeek call failed: category=%s status=%s attempts=%s',
            error.category,
            error.status_code,
            self.max_retries + 1,
        )
        raise error

    @staticmethod
    def _raise_for_status(status_code):
        if 200 <= status_code < 300:
            return
        if status_code == 401:
            raise ProviderCallError('authentication', 'DeepSeek API Key 无效', status_code=401)
        if status_code == 402:
            raise ProviderCallError('quota', 'DeepSeek 账户余额或额度不足', status_code=402)
        if status_code == 429:
            raise ProviderCallError('rate_limit', 'DeepSeek 请求频率受限', retryable=True, status_code=429)
        if status_code >= 500:
            raise ProviderCallError('server', 'DeepSeek 服务暂时不可用', retryable=True, status_code=status_code)
        raise ProviderCallError('http', f'DeepSeek 请求失败（HTTP {status_code}）', status_code=status_code)


class OpenAICompatibleProvider(DeepSeekProvider):
    """Compatibility provider retained for existing deployments."""
    name = 'openai_compatible'

    def __init__(self, config, http_client=requests):
        mapped = dict(config)
        base_url = str(config.get('AI_API_BASE_URL') or '').rstrip('/')
        mapped['DEEPSEEK_API_KEY'] = config.get('AI_API_KEY')
        mapped['DEEPSEEK_BASE_URL'] = base_url
        mapped['DEEPSEEK_CHAT_ENDPOINT'] = '/chat/completions' if base_url.endswith('/v1') else '/v1/chat/completions'
        mapped['DEEPSEEK_MODEL'] = config.get('AI_MODEL')
        mapped['DEEPSEEK_THINKING_ENABLED'] = False
        mapped['AI_TIMEOUT_SECONDS'] = config.get('AI_TIMEOUT', 30)
        super().__init__(mapped, http_client=http_client)

    def call(self, prompt, system_message=None):
        original = self.thinking_enabled
        self.thinking_enabled = False
        try:
            return super().call(prompt, system_message)
        finally:
            self.thinking_enabled = original


def call_ai_api(prompt, system_message=None):
    """Return `(json_text, duration_ms, usage)` or `None` for mock/fallback."""
    provider_name = str(current_app.config.get('AI_PROVIDER', 'mock')).strip().lower()
    if provider_name == 'mock':
        _set_call_state('mock', 'mock', None)
        logger.info('AI provider mode=mock; external request skipped')
        return None

    provider = _build_provider(provider_name)
    fallback_enabled = bool(current_app.config.get('AI_FALLBACK_ENABLED', True))
    try:
        result = provider.call(prompt, system_message)
        _set_call_state('real', provider.name, provider.model)
        return result
    except ProviderCallError as exc:
        if fallback_enabled:
            _set_call_state('fallback', 'mock', None, fallback_from=f'{provider.name}:{provider.model}')
            logger.warning('AI fallback activated: provider=%s category=%s', provider.name, exc.category)
            return None
        raise BusinessError(ErrorCode.AI_ANALYSIS_FAILED, str(exc)) from exc


def _build_provider(provider_name):
    if provider_name in ('deepseek', 'deepseek_v4_pro'):
        return DeepSeekProvider(current_app.config)
    if provider_name == 'openai_compatible':
        return OpenAICompatibleProvider(current_app.config)
    raise BusinessError(ErrorCode.AI_ANALYSIS_FAILED, f'不支持的 AI_PROVIDER: {provider_name}')


def is_mock_mode():
    return str(current_app.config.get('AI_PROVIDER', 'mock')).strip().lower() == 'mock'


def get_mock_provider_info():
    state = _CALL_STATE.get()
    mode = state.get('mode') if state.get('mode') in ('mock', 'fallback') else 'mock'
    return MockProvider().info(mode=mode, fallback_from=state.get('fallback_from'))


def get_provider_info():
    state = _CALL_STATE.get()
    if state.get('mode') == 'real':
        return {
            'provider': state.get('provider'),
            'model': state.get('model'),
            'mode': 'real',
            'is_mock': False,
            'fallback_from': None,
        }
    return get_mock_provider_info()


def attach_result_metadata(result, provider_info, usage=None, trace_id=''):
    result = dict(result or {})
    normalized_usage = _normalize_usage(usage)
    result.update({
        'provider': provider_info.get('provider'),
        'model': provider_info.get('model'),
        'mode': provider_info.get('mode', 'mock' if provider_info.get('is_mock') else 'real'),
        'is_mock': bool(provider_info.get('is_mock')),
        'trace_id': trace_id,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'usage': normalized_usage,
    })
    if provider_info.get('fallback_from'):
        result['fallback_from'] = provider_info['fallback_from']
    return result


def total_tokens(usage):
    return _normalize_usage(usage).get('total_tokens')


def _set_call_state(mode, provider, model, fallback_from=None):
    _CALL_STATE.set({
        'mode': mode,
        'provider': provider,
        'model': model,
        'fallback_from': fallback_from,
    })


def _normalize_usage(usage):
    if isinstance(usage, dict):
        return {
            'prompt_tokens': usage.get('prompt_tokens'),
            'completion_tokens': usage.get('completion_tokens'),
            'total_tokens': usage.get('total_tokens'),
        }
    if isinstance(usage, int):
        return {'prompt_tokens': None, 'completion_tokens': None, 'total_tokens': usage}
    return {'prompt_tokens': None, 'completion_tokens': None, 'total_tokens': None}


def _parse_json_object(content):
    if isinstance(content, dict):
        return content
    text = str(content or '').strip()
    if not text:
        raise ProviderCallError('invalid_json', 'DeepSeek 返回空内容')
    candidates = [text]
    fence = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL | re.IGNORECASE)
    if fence:
        candidates.append(fence.group(1))
    first = text.find('{')
    last = text.rfind('}')
    if first >= 0 and last > first:
        candidates.append(text[first:last + 1])
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    raise ProviderCallError('invalid_json', 'DeepSeek 未返回有效 JSON 对象')


def call_vision_ai_api(prompt, image_bytes, mime_type):
    """Vision remains disabled until the OCR preview/confirm pipeline is used."""
    if current_app.config.get('AI_MOCK_ENABLED', True):
        _set_call_state('mock', 'mock', None)
        logger.info('Vision provider mode=mock; external request skipped')
        return None
    raise BusinessError(
        ErrorCode.AI_ANALYSIS_FAILED,
        '真实图片分析未直接启用，请先通过 OCR 识别并确认文本后再调用 DeepSeek',
    )


def get_vision_provider_info():
    return get_mock_provider_info()
