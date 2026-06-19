from datetime import datetime
from app.extensions import db


class User(db.Model):
    __tablename__ = 'users'

    user_id = db.Column(db.String(20), primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    openid = db.Column(db.String(64), unique=True, nullable=True)
    real_name = db.Column(db.String(20), nullable=False)
    class_name = db.Column(db.String(30), nullable=True, comment='班级名称，学生必填')
    status = db.Column(db.SmallInteger, nullable=False, default=1, comment='1=启用, 0=禁用')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    # 关系
    roles = db.relationship('Role', secondary='user_role', backref=db.backref('users', lazy='dynamic'),
                            lazy='joined')

    def has_role(self, role_name):
        return any(r.role_name == role_name for r in self.roles)

    def get_role_names(self):
        return [r.role_name for r in self.roles]

    def get_permissions(self):
        perms = set()
        for role in self.roles:
            for perm in role.permissions:
                perms.add(perm.permission_code)
        return sorted(perms)

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'username': self.username,
            'real_name': self.real_name,
            'class_name': self.class_name,
            'status': self.status,
            'roles': self.get_role_names(),
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
        }
