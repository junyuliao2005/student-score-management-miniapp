"""
幂等创建 messages 师生互动留言表。

用法:
    cd backend
    python scripts/add_messages_table.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.message import Message


def main():
    app = create_app()
    with app.app_context():
        Message.__table__.create(bind=db.engine, checkfirst=True)
        print('[OK] messages 表已创建或已存在')


if __name__ == '__main__':
    main()
