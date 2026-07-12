"""Create only the AI feedback table; never modifies existing analysis rows."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.ai_feedback import AiAnalysisFeedback


def main():
    app = create_app()
    with app.app_context():
        AiAnalysisFeedback.__table__.create(bind=db.engine, checkfirst=True)
    print('AI feedback table is ready; existing analyses were not modified.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
