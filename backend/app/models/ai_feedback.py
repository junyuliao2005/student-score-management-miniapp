from datetime import datetime

from app.extensions import db


class AiAnalysisFeedback(db.Model):
    __tablename__ = 'ai_analysis_feedback'
    __table_args__ = (
        db.UniqueConstraint('analysis_id', 'user_id', name='uk_ai_feedback_user'),
    )

    id = db.Column(db.BigInteger().with_variant(db.Integer, 'sqlite'), primary_key=True, autoincrement=True)
    analysis_id = db.Column(
        db.BigInteger().with_variant(db.Integer, 'sqlite'),
        db.ForeignKey('ai_analysis.analysis_id'), nullable=False, index=True,
    )
    user_id = db.Column(db.String(20), db.ForeignKey('users.user_id'), nullable=False, index=True)
    rating = db.Column(db.String(20), nullable=False)
    comment = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'analysis_id': self.analysis_id,
            'rating': self.rating,
            'comment': self.comment,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
        }
