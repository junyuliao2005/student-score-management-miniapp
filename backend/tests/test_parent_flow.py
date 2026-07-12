from datetime import date

from app.extensions import db
from app.models.course import Course
from app.models.score import Score

from conftest import auth


def test_parent_binding_published_score_and_confirmation(app, client, login):
    admin = login('admin01')
    parent = login('parent01')
    with app.app_context():
        db.session.add(Course(
            course_id='MATH01', course_name='数学', teacher_id='T001', term='2025-2026-2', status=1,
        ))
        db.session.add(Score(
            student_id='S001', course_id='MATH01', score=90,
            exam_date=date(2026, 4, 10), exam_batch='期中', status=1,
        ))
        db.session.commit()

    binding = client.post('/api/parent-bindings', headers=auth(admin), json={
        'parent_user_id': 'P001', 'student_user_id': 'S001', 'relation': '家长',
    })
    assert binding.get_json()['code'] == 0

    setting = client.post('/api/exam-publish', headers=auth(admin), json={
        'exam_name': '期中发布', 'term': '2025-2026-2', 'exam_batch': '期中',
        'class_name': '2025级1班', 'require_parent_signature': True,
    }).get_json()['data']
    published = client.post(f"/api/exam-publish/{setting['id']}/publish", headers=auth(admin), json={})
    assert published.get_json()['code'] == 0

    children = client.get('/api/parents/my-children', headers=auth(parent)).get_json()['data']
    assert children['children'][0]['student_id'] == 'S001'
    scores = client.get('/api/parents/children/S001/published-scores', headers=auth(parent)).get_json()['data']
    assert len(scores['list']) == 1
    publication = scores['list'][0]
    confirmed = client.post(
        f"/api/parents/confirmations/{publication['publish_id']}/confirm",
        headers=auth(parent), json={'student_id': 'S001', 'signature_text': '测试家长', 'remark': '已阅'},
    )
    assert confirmed.get_json()['data']['confirm_status'] == 'confirmed'


def test_parent_binding_list_respects_teacher_class_scope(app, client, login):
    admin = login('admin01')
    teacher = login('teacher01')
    for student_id in ('S001', 'S010'):
        response = client.post('/api/parent-bindings', headers=auth(admin), json={
            'parent_user_id': 'P001', 'student_user_id': student_id, 'relation': '家长',
        })
        assert response.get_json()['code'] == 0

    scoped = client.put('/api/admin/teacher-bindings/T001', headers=auth(admin), json={
        'class_names': ['2025级1班'], 'course_ids': [],
    })
    assert scoped.get_json()['code'] == 0

    teacher_list = client.get('/api/parent-bindings', headers=auth(teacher)).get_json()['data']
    assert teacher_list['total'] == 1
    assert teacher_list['list'][0]['student_user_id'] == 'S001'

    admin_list = client.get('/api/parent-bindings', headers=auth(admin)).get_json()['data']
    assert admin_list['total'] == 2
