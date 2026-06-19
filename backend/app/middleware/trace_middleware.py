"""trace_id 中间件：为每个请求生成唯一追踪标识"""
from flask import request, g
from app.utils.time_util import generate_trace_id


def init_trace_middleware(app):
    @app.before_request
    def generate_trace_id_for_request():
        trace_id = request.headers.get('X-Trace-Id')
        if not trace_id:
            trace_id = generate_trace_id()
        g.trace_id = trace_id
        request.trace_id = trace_id
