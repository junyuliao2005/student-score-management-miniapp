"""统一响应封装"""
from flask import jsonify, request


def success(data=None, message="success"):
    """成功响应"""
    return jsonify({
        'code': 0,
        'message': message,
        'data': data,
        'trace_id': _get_trace_id(),
    })


def fail(code, message, data=None):
    """失败响应"""
    return jsonify({
        'code': code,
        'message': message,
        'data': data,
        'trace_id': _get_trace_id(),
    })


def _get_trace_id():
    try:
        return getattr(request, 'trace_id', '')
    except RuntimeError:
        return ''
