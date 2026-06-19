from datetime import datetime
from app.extensions import db


class Role(db.Model):
    __tablename__ = 'roles'

    role_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    role_name = db.Column(db.String(30), unique=True, nullable=False)
    description = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    permissions = db.relationship('Permission', secondary='role_permission',
                                  backref=db.backref('roles', lazy='dynamic'), lazy='joined')


class Permission(db.Model):
    __tablename__ = 'permissions'

    permission_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    permission_code = db.Column(db.String(60), unique=True, nullable=False)
    description = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)


class UserRole(db.Model):
    __tablename__ = 'user_role'

    user_id = db.Column(db.String(20), db.ForeignKey('users.user_id'), primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.role_id'), primary_key=True)


class RolePermission(db.Model):
    __tablename__ = 'role_permission'

    role_id = db.Column(db.Integer, db.ForeignKey('roles.role_id'), primary_key=True)
    permission_id = db.Column(db.Integer, db.ForeignKey('permissions.permission_id'), primary_key=True)
