from datetime import datetime
from app.extensions import db

_id_type = db.BigInteger().with_variant(db.Integer, "sqlite")


class AuditLog(db.Model):
    __tablename__ = 'audit_log'

    log_id = db.Column(_id_type, primary_key=True, autoincrement=True)
    trace_id = db.Column(db.String(40), nullable=False)
    operator_id = db.Column(db.String(20), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    target_type = db.Column(db.String(30), nullable=False)
    target_id = db.Column(db.String(50), nullable=False)
    detail_json = db.Column(db.Text, nullable=True)
    result_code = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    __table_args__ = (
        db.Index('idx_audit_trace', 'trace_id'),
        db.Index('idx_audit_operator_time', 'operator_id', 'created_at'),
    )

    def to_dict(self):
        return {
            'log_id': self.log_id,
            'trace_id': self.trace_id,
            'operator_id': self.operator_id,
            'action': self.action,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'detail_json': self.detail_json,
            'result_code': self.result_code,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
        }
