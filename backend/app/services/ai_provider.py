"""
AI Provider 适配器
支持 OpenAI-compatible Chat Completions API 调用。
当 AI_API_KEY 为空或 AI_PROVIDER=mock 时，自动回退到 mock 模式。
"""
import logging
import time

import requests
from flask import current_app

from app.utils.errors import BusinessError, ErrorCode

logger = logging.getLogger(__name__)


def is_mock_mode():
    """
    判断当前是否为 mock 模式。
    - AI_PROVIDER=mock -> True
    - AI_PROVIDER=openai_compatible 且 AI_API_KEY 非空 -> False（真实调用）
    - AI_PROVIDER=openai_compatible 且 AI_API_KEY 为空：
        AI_MOCK_ENABLED=true -> True
        AI_MOCK_ENABLED=false -> False（后续 call_ai_api 会报错）
    - 其他 provider：
        AI_MOCK_ENABLED=true -> True
        AI_MOCK_ENABLED=false -> False
    """
    provider = current_app.config.get('AI_PROVIDER', 'mock')
    api_key = current_app.config.get('AI_API_KEY', '')
    mock_enabled = current_app.config.get('AI_MOCK_ENABLED', True)

    if provider == 'mock':
        return True

    if provider == 'openai_compatible':
        if not api_key:
            return mock_enabled
        return False

    # 其他未识别 provider
    return mock_enabled


def get_mock_provider_info():
    """返回 mock 模式的 provider 信息（用于降级场景）"""
    return {
        'provider': 'mock',
        'model': None,
        'is_mock': True,
    }


def _build_url(base_url):
    """
    兼容两种 base_url 格式：
    - 如果已以 /v1 结尾，则请求 {base_url}/chat/completions
    - 否则请求 {base_url}/v1/chat/completions
    """
    base_url = base_url.rstrip('/')
    if base_url.endswith('/v1'):
        return f'{base_url}/chat/completions'
    return f'{base_url}/v1/chat/completions'


def call_ai_api(prompt, system_message=None):
    """
    调用 AI API（OpenAI-compatible Chat Completions 格式）。

    返回: (result_text, duration_ms, token_used) 或 None（mock 模式）
    """
    if is_mock_mode():
        logger.info('当前为 mock 模式，跳过真实 API 调用')
        return None

    provider = current_app.config.get('AI_PROVIDER', 'mock')
    api_key = current_app.config.get('AI_API_KEY', '')
    base_url = current_app.config.get('AI_API_BASE_URL', '')
    model = current_app.config.get('AI_MODEL', '')
    timeout = current_app.config.get('AI_TIMEOUT', 30)
    mock_enabled = current_app.config.get('AI_MOCK_ENABLED', True)

    # 检查 API Key
    if not api_key:
        if mock_enabled:
            logger.warning('AI_API_KEY 未配置，降级到 mock 模式')
            return None
        raise BusinessError(ErrorCode.AI_ANALYSIS_FAILED, 'AI_API_KEY 未配置')

    # 检查 base_url
    if not base_url:
        if mock_enabled:
            logger.warning('AI_API_BASE_URL 未配置，降级到 mock 模式')
            return None
        raise BusinessError(ErrorCode.AI_ANALYSIS_FAILED, 'AI_API_BASE_URL 未配置')

    # 检查 model
    if not model:
        if mock_enabled:
            logger.warning('AI_MODEL 未配置，降级到 mock 模式')
            return None
        raise BusinessError(ErrorCode.AI_ANALYSIS_FAILED, 'AI_MODEL 未配置')

    url = _build_url(base_url)
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }

    messages = []
    if system_message:
        messages.append({'role': 'system', 'content': system_message})
    messages.append({'role': 'user', 'content': prompt})

    payload = {
        'model': model,
        'messages': messages,
        'temperature': 0.7,
        'max_tokens': 2000,
    }

    start_time = time.time()
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()

        result_text = data['choices'][0]['message']['content']
        duration_ms = int((time.time() - start_time) * 1000)
        token_used = data.get('usage', {}).get('total_tokens')

        return result_text, duration_ms, token_used

    except Exception as e:
        logger.error(f'AI API 调用失败: {e}')
        if mock_enabled:
            logger.info('AI_MOCK_ENABLED=true，降级到 mock 模式')
            return None
        raise BusinessError(ErrorCode.AI_ANALYSIS_FAILED, f'AI API 调用失败: {e}')


def get_provider_info():
    """获取当前 provider 信息"""
    if is_mock_mode():
        return {
            'provider': 'mock',
            'model': None,
            'is_mock': True,
        }

    return {
        'provider': current_app.config.get('AI_PROVIDER', 'mock'),
        'model': current_app.config.get('AI_MODEL', 'qwen-turbo'),
        'is_mock': False,
    }


def call_vision_ai_api(prompt, image_bytes, mime_type):
    """
    视觉模型调用入口预留。

    本课程设计 MVP 默认不主动调用外部视觉 API：
    - mock 开启时返回 None，由上层生成 mock 结果。
    - mock 关闭且配置缺失时返回明确业务错误。
    - 配置完整但 mock 关闭时，保留入口但不发起真实网络请求。
    """
    mock_enabled = current_app.config.get('AI_MOCK_ENABLED', True)
    base_url = current_app.config.get('AI_VISION_API_BASE_URL', '')
    api_key = current_app.config.get('AI_VISION_API_KEY', '')
    model = current_app.config.get('AI_VISION_MODEL', '')

    if mock_enabled:
      logger.info('AI_MOCK_ENABLED=true，视觉分析使用 mock 模式')
      return None

    if not base_url or not api_key or not model:
        raise BusinessError(
            ErrorCode.AI_ANALYSIS_FAILED,
            '视觉模型未配置，请检查 AI_VISION_API_BASE_URL、AI_VISION_API_KEY、AI_VISION_MODEL'
        )

    raise BusinessError(
        ErrorCode.AI_ANALYSIS_FAILED,
        '真实视觉模型调用入口已预留，本版本未启用外部调用'
    )


def get_vision_provider_info():
    """获取视觉 provider 信息。"""
    if current_app.config.get('AI_MOCK_ENABLED', True):
        return get_mock_provider_info()

    return {
        'provider': current_app.config.get('AI_VISION_PROVIDER', 'openai_compatible_vision'),
        'model': current_app.config.get('AI_VISION_MODEL'),
        'is_mock': False,
    }
