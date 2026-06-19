"""师生互动留言模型。"""
from datetime import datetime
from app.extensions import db

_id_type = db.BigInteger().with_variant(db.Integer, "sqlite")


class Message(db.Model):
    __tablename__ = 'messages'

    message_id = db.Column(_id_type, primary_key=True, autoincrement=True)
    sender_id = db.Column(db.String(20), db.ForeignKey('users.user_id'), nullable=False)
    receiver_id = db.Column(db.String(20), db.ForeignKey('users.user_id'), nullable=False)
    course_id = db.Column(db.String(20), db.ForeignKey('courses.course_id'), nullable=True)
    exam_batch = db.Column(db.String(20), nullable=True)
    related_score_id = db.Column(_id_type, db.ForeignKey('scores.score_id'), nullable=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.SmallInteger, nullable=False, default=0)
    read_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.SmallInteger, nullable=False, default=1)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    sender = db.relationship('User', foreign_keys=[sender_id], lazy='joined')
    receiver = db.relationship('User', foreign_keys=[receiver_id], lazy='joined')
    course = db.relationship('Course', foreign_keys=[course_id], lazy='joined')

    def to_dict(self):
        return {
            'message_id': self.message_id,
            'sender_id': self.sender_id,
            'sender_name': self.sender.real_name if self.sender else None,
            'receiver_id': self.receiver_id,
            'receiver_name': self.receiver.real_name if self.receiver else None,
            'course_id': self.course_id,
            'course_name': self.course.course_name if self.course else None,
            'exam_batch': self.exam_batch,
            'related_score_id': self.related_score_id,
            'title': self.title,
            'content': self.content,
            'is_read': bool(self.is_read),
            'read_at': self.read_at.strftime('%Y-%m-%d %H:%M:%S') if self.read_at else None,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
        }
