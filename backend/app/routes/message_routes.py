"""师生互动留言路由。"""
from flask import Blueprint, g, request

from app.middleware.jwt_middleware import jwt_required
from app.services import message_service
from app.utils.response import success

message_bp = Blueprint('message', __name__)


@message_bp.route('/api/messages', methods=['GET'])
@jwt_required
def list_messages():
    """查询当前用户可见的留言列表。"""
    filters = {
        'page': request.args.get('page', 1, type=int),
        'page_size': request.args.get('page_size', 20, type=int),
        'box': request.args.get('box'),
        'unread_only': request.args.get('unread_only'),
        'student_id': request.args.get('student_id'),
        'teacher_id': request.args.get('teacher_id'),
        'course_id': request.args.get('course_id'),
        'exam_batch': request.args.get('exam_batch'),
    }
    result = message_service.list_messages(filters, g.current_user)
    return success(result)


@message_bp.route('/api/messages', methods=['POST'])
@jwt_required
def create_message():
    """创建留言。发送人以后端当前登录用户为准。"""
    data = request.get_json(force=True)
    result = message_service.create_message(
        payload=data,
        current_user=g.current_user,
        trace_id=getattr(request, 'trace_id', ''),
    )
    return success(result)


@message_bp.route('/api/messages/unread-count', methods=['GET'])
@jwt_required
def unread_count():
    """查询当前用户未读留言数量。"""
    result = message_service.unread_count(g.current_user)
    return success(result)


@message_bp.route('/api/messages/<int:message_id>/read', methods=['PUT'])
@jwt_required
def mark_read(message_id):
    """标记单条留言为已读。"""
    result = message_service.mark_read(
        message_id=message_id,
        current_user=g.current_user,
        trace_id=getattr(request, 'trace_id', ''),
    )
    return success(result)


@message_bp.route('/api/messages/read-all', methods=['PUT'])
@jwt_required
def mark_all_read():
    """标记当前用户收到的全部留言为已读。"""
    result = message_service.mark_all_read(
        current_user=g.current_user,
        trace_id=getattr(request, 'trace_id', ''),
    )
    return success(result)


@message_bp.route('/api/messages/contacts', methods=['GET'])
@jwt_required
def list_contacts():
    """查询留言接收人候选列表。"""
    result = message_service.list_contacts(g.current_user)
    return success(result)
