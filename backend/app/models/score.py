from datetime import datetime
from app.extensions import db

_id_type = db.BigInteger().with_variant(db.Integer, "sqlite")


class Score(db.Model):
    __tablename__ = 'scores'

    score_id = db.Column(_id_type, primary_key=True, autoincrement=True)
    student_id = db.Column(db.String(20), db.ForeignKey('users.user_id'), nullable=False)
    course_id = db.Column(db.String(20), db.ForeignKey('courses.course_id'), nullable=False)
    score = db.Column(db.Numeric(5, 2), nullable=False, comment='原始分数 0-100')
    exam_date = db.Column(db.Date, nullable=False)
    exam_batch = db.Column(db.String(20), nullable=False, comment='期中/期末/单元测验/平时')
    status = db.Column(db.SmallInteger, nullable=False, default=1, comment='1=有效, 0=标记删除')

    # 派生字段
    total_score = db.Column(db.Numeric(6, 2), nullable=True, comment='总分缓存')
    avg_score = db.Column(db.Numeric(5, 2), nullable=True, comment='平均分缓存')
    rank_no = db.Column(db.Integer, nullable=True, comment='排名缓存')
    level_tag = db.Column(db.String(10), nullable=True, comment='等级标签')
    comment_text = db.Column(db.String(200), nullable=True, comment='自动评语')
    stat_version = db.Column(db.Integer, nullable=False, default=0, comment='统计版本号')

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    # 关系
    student = db.relationship('User', foreign_keys=[student_id], lazy='joined')
    course = db.relationship('Course', foreign_keys=[course_id], lazy='joined')

    __table_args__ = (
        # status=1 的有效记录保持唯一；status=0 的逻辑删除记录不阻止重新录入
        db.UniqueConstraint('student_id', 'course_id', 'exam_batch', 'status', name='uk_score_once'),
        db.CheckConstraint('score >= 0 AND score <= 100', name='chk_score_range'),
        db.Index('idx_scores_student_course_batch', 'student_id', 'course_id', 'exam_batch'),
        db.Index('idx_scores_course_batch', 'course_id', 'exam_batch'),
        db.Index('idx_scores_rank', 'rank_no'),
    )

    def to_dict(self):
        return {
            'score_id': self.score_id,
            'student_id': self.student_id,
            'student_name': self.student.real_name if self.student else None,
            'class_name': self.student.class_name if self.student else None,
            'course_id': self.course_id,
            'course_name': self.course.course_name if self.course else None,
            'score': float(self.score),
            'exam_date': self.exam_date.strftime('%Y-%m-%d') if self.exam_date else None,
            'exam_batch': self.exam_batch,
            'status': self.status,
            'total_score': float(self.total_score) if self.total_score is not None else None,
            'avg_score': float(self.avg_score) if self.avg_score is not None else None,
            'rank_no': self.rank_no,
            'level_tag': self.level_tag,
            'comment_text': self.comment_text,
            'stat_version': self.stat_version,
        }
