import io
import json

import pytest
from openpyxl import Workbook
from werkzeug.datastructures import FileStorage

from app.services import user_import_service
from app.utils.errors import BusinessError


def _student_workbook():
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(['学号', '姓名', '班级', '用户名', '初始密码'])
    sheet.append(['K12TEST001', '测试学生', '2025级1班', 'k12test001', 'Secret-Only-In-Hash'])
    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return FileStorage(
        stream=buffer,
        filename='students.xlsx',
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


def test_user_import_preview_hides_password_and_is_owner_isolated(app):
    with app.app_context():
        result = user_import_service.preview_import(_student_workbook(), operator_id='A001')
        assert 'password' not in result['rows'][0]
        assert 'password_hash' not in result['rows'][0]
        path = user_import_service._preview_path(result['import_id'])
        cached_text = open(path, encoding='utf-8').read()
        cached = json.loads(cached_text)
        assert 'Secret-Only-In-Hash' not in cached_text
        assert cached['rows'][0]['password_hash']
        with pytest.raises(BusinessError):
            user_import_service._load_preview(result['import_id'], 'OTHER_ADMIN')
        user_import_service._delete_preview(result['import_id'])
