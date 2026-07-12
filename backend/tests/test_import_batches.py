import io
import json
from datetime import date

import pytest
from openpyxl import Workbook
from sqlalchemy import inspect

from app.extensions import db
from app.models.course import Course
from app.models.import_batch import ImportBatch, ImportBatchEntry
from app.models.score import Score
from app.models.user import User
from app.services import import_batch_service, score_import_service

from conftest import auth


def _xlsx(headers, rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer


def _score_file(student_id='S001', score=88):
    return _xlsx(
        ['学号', '课程编号', '分数', '考试日期', '考试批次', '学期'],
        [[student_id, 'MATH01', score, '2026-04-10', '期中', '2025-2026-2']],
    )


def _user_file(rows=None):
    rows = rows or [['K12NEW001', '新学生一', '2025级1班', 'k12new001', 'PlainSecret123']]
    return _xlsx(['学号', '姓名', '班级', '用户名', '初始密码'], rows)


def _prepare_teacher(app, client, admin_token):
    with app.app_context():
        db.session.add(Course(
            course_id='MATH01', course_name='数学', teacher_id='T001', term='2025-2026-2', status=1,
        ))
        db.session.commit()
    response = client.put('/api/admin/teacher-bindings/T001', headers=auth(admin_token), json={
        'class_names': ['2025级1班'], 'course_ids': ['MATH01'],
    })
    assert response.get_json()['code'] == 0


def _preview_score(client, teacher_token, file_obj=None):
    response = client.post(
        '/api/scores/import/preview',
        headers=auth(teacher_token),
        data={'file': (file_obj or _score_file(), 'scores.xlsx')},
        content_type='multipart/form-data',
    )
    payload = response.get_json()
    assert payload['code'] == 0
    return payload['data']


def _preview_user(client, admin_token, file_obj=None):
    response = client.post(
        '/api/users/import/preview',
        headers=auth(admin_token),
        data={'file': (file_obj or _user_file(), 'students.xlsx')},
        content_type='multipart/form-data',
    )
    payload = response.get_json()
    assert payload['code'] == 0
    return payload['data']


def test_score_import_creates_ledger_only_on_confirm_and_rolls_back(app, client, login):
    admin = login('admin01')
    teacher = login('teacher01')
    _prepare_teacher(app, client, admin)
    preview = _preview_score(client, teacher)
    with app.app_context():
        assert ImportBatch.query.count() == 0

    confirmed = client.post('/api/scores/import/confirm', headers=auth(teacher), json={
        'import_id': preview['import_id'],
    }).get_json()['data']
    assert confirmed['import_batch_id']
    with app.app_context():
        batch = ImportBatch.query.filter_by(import_batch_id=confirmed['import_batch_id']).one()
        entry = ImportBatchEntry.query.filter_by(import_batch_id=batch.import_batch_id).one()
        assert batch.status == 'completed'
        assert batch.success_rows == 1
        assert entry.entity_type == 'score'
        assert entry.action_type == 'create'

    denied = client.post(
        f"/api/import-batches/{confirmed['import_batch_id']}/rollback",
        headers=auth(teacher), json={},
    )
    assert denied.status_code == 403
    rolled_back = client.post(
        f"/api/import-batches/{confirmed['import_batch_id']}/rollback",
        headers=auth(admin), json={},
    ).get_json()['data']
    assert rolled_back['success_count'] == 1
    with app.app_context():
        assert Score.query.one().status == 0
    repeated = client.post(
        f"/api/import-batches/{confirmed['import_batch_id']}/rollback",
        headers=auth(admin), json={},
    )
    assert repeated.status_code == 403


def test_user_import_ledger_snapshot_has_no_secrets_and_safe_disable(app, client, login):
    admin = login('admin01')
    preview = _preview_user(client, admin)
    with app.app_context():
        assert ImportBatch.query.count() == 0
    confirmed = client.post('/api/users/import/confirm', headers=auth(admin), json={
        'import_id': preview['import_id'],
    }).get_json()['data']
    detail_response = client.get(
        f"/api/import-batches/{confirmed['import_batch_id']}", headers=auth(admin),
    )
    detail_text = detail_response.get_data(as_text=True).lower()
    assert detail_response.get_json()['code'] == 0
    for secret in ('plainsecret123', 'password_hash', 'authorization', 'api_key', 'token'):
        assert secret not in detail_text

    result = client.post(
        f"/api/import-batches/{confirmed['import_batch_id']}/rollback",
        headers=auth(admin), json={},
    ).get_json()['data']
    assert result['success_count'] == 1
    with app.app_context():
        assert User.query.filter_by(user_id='K12NEW001').one().status == 0


def test_partial_user_rollback_skips_business_reference(app, client, login):
    admin = login('admin01')
    rows = [
        ['K12NEW001', '新学生一', '2025级1班', 'k12new001', '123456'],
        ['K12NEW002', '新学生二', '2025级1班', 'k12new002', '123456'],
    ]
    preview = _preview_user(client, admin, _user_file(rows))
    confirmed = client.post('/api/users/import/confirm', headers=auth(admin), json={
        'import_id': preview['import_id'],
    }).get_json()['data']
    with app.app_context():
        db.session.add(Course(
            course_id='MATH01', course_name='数学', teacher_id='T001', term='2025-2026-2', status=1,
        ))
        db.session.add(Score(
            student_id='K12NEW001', course_id='MATH01', score=80,
            exam_date=date(2026, 4, 10), exam_batch='期中', status=1,
        ))
        db.session.commit()
    rollback = client.post(
        f"/api/import-batches/{confirmed['import_batch_id']}/rollback",
        headers=auth(admin), json={},
    ).get_json()['data']
    assert rollback['status'] == 'rollback_partial'
    assert rollback['success_count'] == 1
    assert rollback['skipped_count'] == 1
    with app.app_context():
        assert User.query.filter_by(user_id='K12NEW001').one().status == 1
        assert User.query.filter_by(user_id='K12NEW002').one().status == 0


def test_modified_score_is_not_overwritten_by_rollback(app, client, login):
    admin = login('admin01')
    teacher = login('teacher01')
    _prepare_teacher(app, client, admin)
    preview = _preview_score(client, teacher)
    confirmed = client.post('/api/scores/import/confirm', headers=auth(teacher), json={
        'import_id': preview['import_id'],
    }).get_json()['data']
    with app.app_context():
        score = Score.query.one()
        score.score = 99
        db.session.commit()
    rollback = client.post(
        f"/api/import-batches/{confirmed['import_batch_id']}/rollback",
        headers=auth(admin), json={},
    ).get_json()['data']
    assert rollback['status'] == 'rollback_partial'
    assert rollback['skipped_count'] == 1
    with app.app_context():
        score = Score.query.one()
        assert float(score.score) == 99
        assert score.status == 1


def test_update_entry_restores_before_snapshot(app, client, login):
    admin = login('admin01')
    with app.app_context():
        db.session.add(Course(
            course_id='MATH01', course_name='数学', teacher_id='T001', term='2025-2026-2', status=1,
        ))
        score = Score(
            student_id='S001', course_id='MATH01', score=70,
            exam_date=date(2026, 4, 10), exam_batch='期中', status=1,
        )
        db.session.add(score)
        db.session.flush()
        before = import_batch_service.score_snapshot(score)
        batch = import_batch_service.create_batch('scores', 'A001', 'update.xlsx', 1)
        score.score = 85
        import_batch_service.record_score_entry(batch, score, row_number=2, action_type='update', before=before)
        import_batch_service.complete_batch(batch, 1, 0)
        batch_id = batch.import_batch_id
        db.session.commit()
    rollback = client.post(f'/api/import-batches/{batch_id}/rollback', headers=auth(admin), json={})
    assert rollback.get_json()['data']['success_count'] == 1
    with app.app_context():
        assert float(Score.query.one().score) == 70


def test_confirm_failure_rolls_back_score_and_completed_batch(app, client, login, monkeypatch):
    admin = login('admin01')
    teacher = login('teacher01')
    _prepare_teacher(app, client, admin)
    preview = _preview_score(client, teacher)

    def fail_entry(*args, **kwargs):
        raise RuntimeError('forced ledger failure')

    monkeypatch.setattr(score_import_service.import_batch_service, 'record_score_entry', fail_entry)
    response = client.post('/api/scores/import/confirm', headers=auth(teacher), json={
        'import_id': preview['import_id'],
    })
    assert response.status_code == 500
    with app.app_context():
        assert Score.query.count() == 0
        assert ImportBatch.query.filter_by(status='completed').count() == 0


def test_import_tables_and_mysql_migration_are_non_destructive(app):
    with app.app_context():
        tables = set(inspect(db.engine).get_table_names())
        assert {'import_batches', 'import_batch_entries'} <= tables
    sql = open('sql/add_import_batch_tables.sql', encoding='utf-8').read().upper()
    assert 'CREATE TABLE IF NOT EXISTS IMPORT_BATCHES' in sql
    assert 'CREATE TABLE IF NOT EXISTS IMPORT_BATCH_ENTRIES' in sql
    for forbidden in ('DROP TABLE', 'DROP DATABASE', 'TRUNCATE', 'DELETE FROM'):
        assert forbidden not in sql
