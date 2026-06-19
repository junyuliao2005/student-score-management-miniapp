"""可选执行：创建 parent01 并绑定一个初中、一个高中真实学生。

用法：
    cd backend
    python scripts/seed_parent_demo.py

脚本幂等执行，不清空任何数据，不覆盖已有密码。
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models.role import Role, UserRole  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.score import Score  # noqa: E402
from app.models.exam_publish import ParentStudentBinding  # noqa: E402
from app.utils.hash_util import hash_password  # noqa: E402


def pick_student(prefix):
    return db.session.query(User).join(Score, Score.student_id == User.user_id).filter(
        User.status == 1,
        User.class_name.like(f'{prefix}%'),
        Score.status == 1,
    ).group_by(User.user_id).order_by(db.func.count(Score.score_id).desc()).first()


def ensure_parent():
    role = Role.query.filter_by(role_name='parent').first()
    if not role:
        role = Role(role_name='parent', description='家长')
        db.session.add(role)
        db.session.flush()

    parent = User.query.filter_by(username='parent01').first()
    if not parent:
        parent = User(
            user_id='PARENT01',
            username='parent01',
            password_hash=hash_password('123456'),
            real_name='测试家长',
            class_name=None,
            status=1,
        )
        db.session.add(parent)
        db.session.flush()

    if not UserRole.query.filter_by(user_id=parent.user_id, role_id=role.role_id).first():
        db.session.add(UserRole(user_id=parent.user_id, role_id=role.role_id))

    return parent


def bind(parent, student, relation):
    if not student:
        return None
    existing = ParentStudentBinding.query.filter_by(
        parent_user_id=parent.user_id,
        student_user_id=student.user_id,
    ).first()
    if existing:
        existing.status = 1
        existing.relation = existing.relation or relation
        return existing
    binding = ParentStudentBinding(
        parent_user_id=parent.user_id,
        student_user_id=student.user_id,
        relation=relation,
        status=1,
    )
    db.session.add(binding)
    return binding


def main():
    app = create_app()
    with app.app_context():
        parent = ensure_parent()
        junior = pick_student('初')
        senior = pick_student('高')
        bind(parent, junior, '家长')
        bind(parent, senior, '家长')
        db.session.commit()
        print('parent01 / 123456 已准备好')
        if junior:
            print(f'绑定初中学生: {junior.username} {junior.real_name} {junior.class_name}')
        if senior:
            print(f'绑定高中学生: {senior.username} {senior.real_name} {senior.class_name}')


if __name__ == '__main__':
    main()
