"""系统配置读取服务"""
import json
import logging
from app.models.sys_config import SysConfig
from app.utils.errors import BusinessError, ErrorCode

logger = logging.getLogger(__name__)

# 内存缓存，只缓存纯 Python 值，不缓存 ORM 对象
_config_cache = {}


def _load_config_value(key):
    """从数据库读取配置项，缓存纯字典而非 ORM 对象"""
    if key in _config_cache:
        return _config_cache[key]
    config = SysConfig.query.filter_by(config_key=key).first()
    if config:
        value = {
            'config_value': config.config_value,
            'config_type': config.config_type,
            'scope': config.scope,
            'remark': config.remark,
        }
        _config_cache[key] = value
        return value
    return None


def get_config(key, default=None):
    """获取配置值（字符串）"""
    item = _load_config_value(key)
    if item:
        return item['config_value']
    if default is not None:
        return default
    return None


def get_int(key, default=None):
    """获取整型配置值"""
    val = get_config(key)
    if val is not None:
        try:
            return int(val)
        except (ValueError, TypeError):
            pass
    if default is not None:
        return default
    raise BusinessError(ErrorCode.CONFIG_MISSING, f'配置项缺失: {key}',
                        data={'config_key': key})


def get_json(key, default=None):
    """获取 JSON 配置值"""
    val = get_config(key)
    if val is not None:
        try:
            return json.loads(val)
        except json.JSONDecodeError:
            pass
    if default is not None:
        return default
    raise BusinessError(ErrorCode.CONFIG_MISSING, f'配置项缺失: {key}',
                        data={'config_key': key})


def get_bool(key, default=False):
    """获取布尔型配置值"""
    val = get_config(key)
    if val is not None:
        return val.lower() in ('1', 'true', 'yes')
    return default


def clear_cache():
    """清除配置缓存（配置更新后调用）"""
    global _config_cache
    _config_cache = {}
