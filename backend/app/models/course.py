from datetime import datetime
from app.extensions import db


class Course(db.Model):
    __tablename__ = 'courses'

    course_id = db.Column(db.String(20), primary_key=True)
    course_name = db.Column(db.String(50), unique=True, nullable=False)
    teacher_id = db.Column(db.String(20), db.ForeignKey('users.user_id'), nullable=False)
    term = db.Column(db.String(20), nullable=False)
    credit = db.Column(db.Numeric(3, 1), nullable=True)
    status = db.Column(db.SmallInteger, nullable=False, default=1, comment='1=启用, 0=停用')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    teacher = db.relationship('User', foreign_keys=[teacher_id], lazy='joined')

    def to_dict(self):
        return {
            'course_id': self.course_id,
            'course_name': self.course_name,
            'teacher_id': self.teacher_id,
            'teacher_name': self.teacher.real_name if self.teacher else None,
            'term': self.term,
            'credit': float(self.credit) if self.credit else None,
            'status': self.status,
        }
