from datetime import datetime

from app.extensions import db

_entry_id_type = db.BigInteger().with_variant(db.Integer, 'sqlite')


class ImportBatch(db.Model):
    __tablename__ = 'import_batches'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    import_batch_id = db.Column(db.String(36), unique=True, nullable=False, index=True)
    import_type = db.Column(db.String(20), nullable=False, index=True)
    operator_user_id = db.Column(db.String(20), db.ForeignKey('users.user_id'), nullable=False, index=True)
    source_filename = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(30), nullable=False, default='processing', index=True)
    total_rows = db.Column(db.Integer, nullable=False, default=0)
    success_rows = db.Column(db.Integer, nullable=False, default=0)
    failed_rows = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    completed_at = db.Column(db.DateTime, nullable=True)
    rolled_back_at = db.Column(db.DateTime, nullable=True)
    rollback_operator_user_id = db.Column(db.String(20), db.ForeignKey('users.user_id'), nullable=True)
    rollback_summary = db.Column(db.Text, nullable=True)
    metadata_json = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'import_batch_id': self.import_batch_id,
            'import_type': self.import_type,
            'operator_user_id': self.operator_user_id,
            'source_filename': self.source_filename,
            'status': self.status,
            'total_rows': self.total_rows,
            'success_rows': self.success_rows,
            'failed_rows': self.failed_rows,
            'created_at': _format_time(self.created_at),
            'completed_at': _format_time(self.completed_at),
            'rolled_back_at': _format_time(self.rolled_back_at),
            'rollback_operator_user_id': self.rollback_operator_user_id,
        }


class ImportBatchEntry(db.Model):
    __tablename__ = 'import_batch_entries'
    __table_args__ = (
        db.UniqueConstraint(
            'import_batch_id', 'entity_type', 'entity_id', 'action_type',
            name='uk_import_batch_entry',
        ),
    )

    id = db.Column(_entry_id_type, primary_key=True, autoincrement=True)
    import_batch_id = db.Column(
        db.String(36), db.ForeignKey('import_batches.import_batch_id'), nullable=False, index=True,
    )
    entity_type = db.Column(db.String(20), nullable=False)
    entity_id = db.Column(db.String(50), nullable=False)
    action_type = db.Column(db.String(20), nullable=False)
    before_snapshot = db.Column(db.Text, nullable=True)
    after_snapshot = db.Column(db.Text, nullable=False)
    row_number = db.Column(db.Integer, nullable=True)
    rollback_status = db.Column(db.String(20), nullable=True)
    rollback_reason = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    def to_dict(self, include_snapshots=False):
        data = {
            'id': self.id,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'action_type': self.action_type,
            'row_number': self.row_number,
            'rollback_status': self.rollback_status,
            'rollback_reason': self.rollback_reason,
            'created_at': _format_time(self.created_at),
        }
        if include_snapshots:
            data['before_snapshot'] = self.before_snapshot
            data['after_snapshot'] = self.after_snapshot
        return data


def _format_time(value):
    return value.strftime('%Y-%m-%d %H:%M:%S') if value else None
