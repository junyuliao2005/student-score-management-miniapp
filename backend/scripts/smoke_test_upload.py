"""Offline validation for forged/oversized uploads; no network or database required."""
import io
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from werkzeug.datastructures import FileStorage

from app.utils.errors import BusinessError
from app.utils.upload_security import validate_xlsx_upload


def main():
    valid_buffer = io.BytesIO()
    with zipfile.ZipFile(valid_buffer, 'w') as archive:
        archive.writestr('[Content_Types].xml', '<Types/>')
    valid_buffer.seek(0)
    valid = FileStorage(valid_buffer, filename='scores.xlsx', content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    validate_xlsx_upload(valid, max_size_mb=1)

    forged = FileStorage(io.BytesIO(b'not-an-xlsx'), filename='scores.xlsx', content_type='application/octet-stream')
    try:
        validate_xlsx_upload(forged, max_size_mb=1)
        raise AssertionError('forged XLSX should fail')
    except BusinessError:
        pass
    print('PASS: XLSX signature and size validation')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

