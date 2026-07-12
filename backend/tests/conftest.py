import os
import shutil
import uuid

import pytest

from app import create_app
from app.extensions import db
from app.models.role import Role, UserRole
from app.models.user import User
from app.utils.hash_util import hash_password
from config import TestConfig
from scripts.init_db import seed_demo_users, seed_roles_permissions, seed_sys_config


@pytest.fixture()
def app():
    runtime_root = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        '.runtime', f'pytest-{uuid.uuid4().hex}',
    )
    os.makedirs(runtime_root, exist_ok=True)
    flask_app = create_app(TestConfig)
    flask_app.config.update(
        SCORE_IMPORT_PREVIEW_DIR=os.path.join(runtime_root, 'score-previews'),
        USER_IMPORT_PREVIEW_DIR=os.path.join(runtime_root, 'user-previews'),
        OCR_PREVIEW_DIR=os.path.join(runtime_root, 'ocr-previews'),
        IMPORT_PREVIEW_TTL_SECONDS=1800,
        AI_PROVIDER='mock',
        OCR_PROVIDER='mock',
    )
    with flask_app.app_context():
        db.create_all()
        seed_roles_permissions(flask_app)
        seed_sys_config(flask_app)
        seed_demo_users(flask_app)
        User.query.filter_by(user_id='S010').update({'class_name': '2025级2班'})
        parent_role = Role.query.filter_by(role_name='parent').first()
        if not parent_role:
            parent_role = Role(role_name='parent', description='家长')
            db.session.add(parent_role)
            db.session.flush()
        parent = User(
            user_id='P001', username='parent01', password_hash=hash_password('123456'),
            real_name='测试家长', status=1,
        )
        db.session.add(parent)
        db.session.flush()
        db.session.add(UserRole(user_id=parent.user_id, role_id=parent_role.role_id))
        db.session.commit()
        yield flask_app
        db.session.remove()
        db.drop_all()
    shutil.rmtree(runtime_root, ignore_errors=True)


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def login(client):
    def _login(username, password='123456'):
        response = client.post('/api/auth/login', json={'username': username, 'password': password})
        payload = response.get_json()
        assert payload['code'] == 0
        return payload['data']['token']
    return _login


def auth(token):
    return {'Authorization': f'Bearer {token}'}
