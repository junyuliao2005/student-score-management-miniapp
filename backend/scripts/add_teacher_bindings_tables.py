"""Create only the teacher binding tables. Does not initialize or clear data."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.teacher_binding import TeacherClassBinding, TeacherCourseBinding


def main():
    app = create_app()
    with app.app_context():
        TeacherClassBinding.__table__.create(bind=db.engine, checkfirst=True)
        TeacherCourseBinding.__table__.create(bind=db.engine, checkfirst=True)
    print('Teacher binding tables are ready; existing data was not modified.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
