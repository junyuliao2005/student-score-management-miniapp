from datetime import datetime
from app.extensions import db

_id_type = db.BigInteger().with_variant(db.Integer, "sqlite")


class AiAnalysis(db.Model):
    __tablename__ = 'ai_analysis'

    analysis_id = db.Column(_id_type, primary_key=True, autoincrement=True)
    analysis_type = db.Column(db.String(30), nullable=False,
                              comment='student_advice/class_overview/exam_paper/combined')
    target_id = db.Column(db.String(50), nullable=False, comment='学生ID/班级ID/试卷ID')
    input_snapshot = db.Column(db.Text, nullable=True, comment='本次分析数据快照JSON')
    prompt_text = db.Column(db.Text, nullable=True, comment='提示词(可选保存,脱敏)')
    result_text = db.Column(db.Text, nullable=False, comment='AI返回结果')
    provider = db.Column(db.String(20), nullable=False, default='mock', comment='mock/free_api/custom_api')
    model_name = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(10), nullable=False, default='success', comment='success/failed')
    error_message = db.Column(db.String(500), nullable=True)
    token_used = db.Column(db.Integer, nullable=True)
    duration_ms = db.Column(db.Integer, nullable=True)
    created_by = db.Column(db.String(20), db.ForeignKey('users.user_id'), nullable=False)
    trace_id = db.Column(db.String(40), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    creator = db.relationship('User', foreign_keys=[created_by], lazy='joined')

    __table_args__ = (
        db.Index('idx_ai_analysis_type', 'analysis_type'),
        db.Index('idx_ai_analysis_target', 'target_id'),
        db.Index('idx_ai_analysis_creator', 'created_by', 'created_at'),
    )

    def to_dict(self):
        return {
            'analysis_id': self.analysis_id,
            'analysis_type': self.analysis_type,
            'target_id': self.target_id,
            'result_text': self.result_text,
            'provider': self.provider,
            'model_name': self.model_name,
            'status': self.status,
            'created_by': self.created_by,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
        }
