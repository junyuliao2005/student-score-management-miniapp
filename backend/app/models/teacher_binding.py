from datetime import datetime

from app.extensions import db


class TeacherClassBinding(db.Model):
    __tablename__ = 'teacher_class_bindings'
    __table_args__ = (
        db.UniqueConstraint('teacher_id', 'class_name', name='uk_teacher_class_binding'),
    )

    binding_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    teacher_id = db.Column(db.String(20), db.ForeignKey('users.user_id'), nullable=False, index=True)
    class_name = db.Column(db.String(30), nullable=False, index=True)
    status = db.Column(db.SmallInteger, nullable=False, default=1)
    created_by = db.Column(db.String(20), db.ForeignKey('users.user_id'), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'binding_id': self.binding_id,
            'teacher_id': self.teacher_id,
            'class_name': self.class_name,
            'status': self.status,
        }


class TeacherCourseBinding(db.Model):
    __tablename__ = 'teacher_course_bindings'
    __table_args__ = (
        db.UniqueConstraint('teacher_id', 'course_id', name='uk_teacher_course_binding'),
    )

    binding_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    teacher_id = db.Column(db.String(20), db.ForeignKey('users.user_id'), nullable=False, index=True)
    course_id = db.Column(db.String(20), db.ForeignKey('courses.course_id'), nullable=False, index=True)
    status = db.Column(db.SmallInteger, nullable=False, default=1)
    created_by = db.Column(db.String(20), db.ForeignKey('users.user_id'), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'binding_id': self.binding_id,
            'teacher_id': self.teacher_id,
            'course_id': self.course_id,
            'status': self.status,
        }
