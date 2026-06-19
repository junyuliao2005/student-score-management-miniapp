"""审计日志服务"""
import json
import logging
from app.extensions import db
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


def write(action, operator_id, target_type, target_id,
          detail=None, trace_id='', result_code=0):
    """写入审计日志。失败不影响主流程。"""
    try:
        detail_json = json.dumps(detail, ensure_ascii=False) if detail else None
        log = AuditLog(
            trace_id=trace_id,
            operator_id=operator_id,
            action=action,
            target_type=target_type,
            target_id=str(target_id),
            detail_json=detail_json,
            result_code=result_code,
        )
        db.session.add(log)
        db.session.flush()
    except Exception as e:
        logger.error(f'审计日志写入失败: {e}')
        # 不抛出异常，不影响主业务流程
