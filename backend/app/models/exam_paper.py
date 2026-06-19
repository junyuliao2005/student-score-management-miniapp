from datetime import datetime
from app.extensions import db

_id_type = db.BigInteger().with_variant(db.Integer, "sqlite")


class ExamPaper(db.Model):
    __tablename__ = 'exam_paper'

    paper_id = db.Column(_id_type, primary_key=True, autoincrement=True)
    title = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(50), nullable=False)
    exam_batch = db.Column(db.String(20), nullable=True)
    raw_text = db.Column(db.Text, nullable=False, comment='试卷原始文本')
    key_points_json = db.Column(db.Text, nullable=True, comment='考点分析结果JSON')
    difficulty_level = db.Column(db.String(10), nullable=True, comment='简单/中等/较难')
    question_count = db.Column(db.Integer, nullable=True)
    created_by = db.Column(db.String(20), db.ForeignKey('users.user_id'), nullable=False)
    trace_id = db.Column(db.String(40), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    creator = db.relationship('User', foreign_keys=[created_by], lazy='joined')

    def to_dict(self):
        return {
            'paper_id': self.paper_id,
            'title': self.title,
            'subject': self.subject,
            'exam_batch': self.exam_batch,
            'difficulty_level': self.difficulty_level,
            'question_count': self.question_count,
            'created_by': self.created_by,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
        }
