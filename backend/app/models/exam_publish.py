from datetime import datetime
from app.extensions import db


_id_type = db.BigInteger().with_variant(db.Integer, "sqlite")


class ExamPublishSetting(db.Model):
    __tablename__ = 'exam_publish_settings'

    id = db.Column(_id_type, primary_key=True, autoincrement=True)
    exam_name = db.Column(db.String(100), nullable=False)
    term = db.Column(db.String(50), nullable=False)
    exam_batch = db.Column(db.String(100), nullable=False)
    grade_name = db.Column(db.String(50), nullable=True)
    class_name = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='draft')
    show_total = db.Column(db.SmallInteger, nullable=False, default=1)
    show_rank = db.Column(db.SmallInteger, nullable=False, default=1)
    show_grade_rank = db.Column(db.SmallInteger, nullable=False, default=1)
    show_class_average = db.Column(db.SmallInteger, nullable=False, default=1)
    show_subject_scores = db.Column(db.SmallInteger, nullable=False, default=1)
    require_parent_signature = db.Column(db.SmallInteger, nullable=False, default=0)
    publish_time = db.Column(db.DateTime, nullable=True)
    withdraw_time = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'exam_name': self.exam_name,
            'term': self.term,
            'exam_batch': self.exam_batch,
            'grade_name': self.grade_name,
            'class_name': self.class_name,
            'status': self.status,
            'show_total': bool(self.show_total),
            'show_rank': bool(self.show_rank),
            'show_grade_rank': bool(self.show_grade_rank),
            'show_class_average': bool(self.show_class_average),
            'show_subject_scores': bool(self.show_subject_scores),
            'require_parent_signature': bool(self.require_parent_signature),
            'publish_time': self.publish_time.strftime('%Y-%m-%d %H:%M:%S') if self.publish_time else None,
            'withdraw_time': self.withdraw_time.strftime('%Y-%m-%d %H:%M:%S') if self.withdraw_time else None,
            'created_by': self.created_by,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
        }


class ParentStudentBinding(db.Model):
    __tablename__ = 'parent_student_bindings'

    id = db.Column(_id_type, primary_key=True, autoincrement=True)
    parent_user_id = db.Column(db.String(50), nullable=False)
    student_user_id = db.Column(db.String(50), nullable=False)
    relation = db.Column(db.String(50), nullable=True, default='家长')
    status = db.Column(db.SmallInteger, nullable=False, default=1)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'parent_user_id': self.parent_user_id,
            'student_user_id': self.student_user_id,
            'relation': self.relation,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
        }


class ParentScoreConfirmation(db.Model):
    __tablename__ = 'parent_score_confirmations'

    id = db.Column(_id_type, primary_key=True, autoincrement=True)
    publish_id = db.Column(_id_type, nullable=False)
    parent_user_id = db.Column(db.String(50), nullable=False)
    student_user_id = db.Column(db.String(50), nullable=False)
    confirm_status = db.Column(db.String(20), nullable=False, default='pending')
    signature_text = db.Column(db.String(100), nullable=True)
    confirmed_at = db.Column(db.DateTime, nullable=True)
    remark = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'publish_id': self.publish_id,
            'parent_user_id': self.parent_user_id,
            'student_user_id': self.student_user_id,
            'confirm_status': self.confirm_status,
            'signature_text': self.signature_text,
            'confirmed_at': self.confirmed_at.strftime('%Y-%m-%d %H:%M:%S') if self.confirmed_at else None,
            'remark': self.remark,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
        }
