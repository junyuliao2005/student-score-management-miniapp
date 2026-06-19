"""统一异常处理器"""
import logging
from flask import jsonify, request
from app.utils.errors import BusinessError

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    @app.errorhandler(BusinessError)
    def handle_business_error(e):
        logger.warning(f'BusinessError: code={e.code} msg={e.message}')
        return jsonify({
            'code': e.code,
            'message': e.message,
            'data': e.data,
            'trace_id': getattr(request, 'trace_id', ''),
        }), e.http_status

    @app.errorhandler(404)
    def handle_not_found(e):
        return jsonify({
            'code': 50003,
            'message': 'NOT_FOUND',
            'data': None,
            'trace_id': getattr(request, 'trace_id', ''),
        }), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(e):
        return jsonify({
            'code': 50003,
            'message': 'METHOD_NOT_ALLOWED',
            'data': None,
            'trace_id': getattr(request, 'trace_id', ''),
        }), 405

    @app.errorhandler(500)
    def handle_internal_error(e):
        logger.error(f'InternalError: {e}')
        return jsonify({
            'code': 50003,
            'message': 'INTERNAL_SERVER_ERROR',
            'data': None,
            'trace_id': getattr(request, 'trace_id', ''),
        }), 500

    @app.errorhandler(Exception)
    def handle_generic_exception(e):
        logger.error(f'UnhandledException: {type(e).__name__}: {e}', exc_info=True)
        return jsonify({
            'code': 50003,
            'message': 'INTERNAL_SERVER_ERROR',
            'data': None,
            'trace_id': getattr(request, 'trace_id', ''),
        }), 500
