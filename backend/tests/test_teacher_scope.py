from app.extensions import db
from app.models.course import Course
from app.models.teacher_binding import TeacherClassBinding, TeacherCourseBinding

from conftest import auth


def _seed_courses():
    db.session.add_all([
        Course(course_id='MATH01', course_name='数学', teacher_id='T001', term='2025-2026-2', status=1),
        Course(course_id='ENG01', course_name='英语', teacher_id='T001', term='2025-2026-2', status=1),
    ])
    db.session.commit()


def test_teacher_scope_default_deny_and_explicit_allow(app, client, login):
    admin = login('admin01')
    teacher = login('teacher01')
    with app.app_context():
        _seed_courses()

    denied = client.post('/api/scores', headers=auth(teacher), json={
        'student_id': 'S001', 'course_id': 'MATH01', 'score': 88,
        'exam_date': '2026-04-10', 'exam_batch': '期中',
    })
    assert denied.status_code == 403
    assert denied.get_json()['code'] == 30001

    saved = client.put('/api/admin/teacher-bindings/T001', headers=auth(admin), json={
        'class_names': ['2025级1班'], 'course_ids': ['MATH01'],
    })
    assert saved.get_json()['code'] == 0

    allowed = client.post('/api/scores', headers=auth(teacher), json={
        'student_id': 'S001', 'course_id': 'MATH01', 'score': 88,
        'exam_date': '2026-04-10', 'exam_batch': '期中',
    })
    assert allowed.get_json()['code'] == 0

    wrong_class = client.post('/api/scores', headers=auth(teacher), json={
        'student_id': 'S010', 'course_id': 'MATH01', 'score': 77,
        'exam_date': '2026-04-10', 'exam_batch': '期中',
    })
    wrong_course = client.post('/api/scores', headers=auth(teacher), json={
        'student_id': 'S002', 'course_id': 'ENG01', 'score': 77,
        'exam_date': '2026-04-10', 'exam_batch': '期中',
    })
    assert wrong_class.status_code == 403
    assert wrong_course.status_code == 403

    listed = client.get('/api/scores', headers=auth(teacher)).get_json()['data']
    assert listed['total'] == 1
    assert listed['list'][0]['student_id'] == 'S001'


def test_binding_replacement_is_soft_disable(app, client, login):
    admin = login('admin01')
    with app.app_context():
        _seed_courses()
    assert client.put('/api/admin/teacher-bindings/T001', headers=auth(admin), json={
        'class_names': ['2025级1班'], 'course_ids': ['MATH01', 'ENG01'],
    }).get_json()['code'] == 0
    assert client.put('/api/admin/teacher-bindings/T001', headers=auth(admin), json={
        'class_names': [], 'course_ids': ['MATH01'],
    }).get_json()['code'] == 0
    with app.app_context():
        assert TeacherClassBinding.query.filter_by(teacher_id='T001', status=0).count() == 1
        assert TeacherCourseBinding.query.filter_by(teacher_id='T001', status=0).count() == 1
