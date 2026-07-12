"""Create only import ledger tables; never initializes or clears business data."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.import_batch import ImportBatch, ImportBatchEntry


def main():
    app = create_app()
    with app.app_context():
        ImportBatch.__table__.create(bind=db.engine, checkfirst=True)
        ImportBatchEntry.__table__.create(bind=db.engine, checkfirst=True)
    print('Import ledger tables are ready; existing users and scores were not modified.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
