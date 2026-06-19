"""时间工具"""
import time
import uuid
from datetime import datetime


def now_str():
    """当前时间格式化字符串"""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def today_str():
    """当前日期格式化字符串"""
    return datetime.now().strftime('%Y-%m-%d')


def generate_trace_id():
    """生成 trace_id: 时间戳-8位随机串"""
    ts = time.strftime('%Y%m%d%H%M%S')
    rand = uuid.uuid4().hex[:8]
    return f'{ts}-{rand}'
