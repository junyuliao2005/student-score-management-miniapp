from datetime import date

from app.extensions import db
from app.models.course import Course
from app.models.score import Score

from conftest import auth


def test_student_sees_only_published_scores(app, client, login):
    admin = login('admin01')
    student = login('student01')
    with app.app_context():
        db.session.add(Course(
            course_id='MATH01', course_name='数学', teacher_id='T001', term='2025-2026-2', status=1,
        ))
        db.session.add(Score(
            student_id='S001', course_id='MATH01', score=92,
            exam_date=date(2026, 4, 10), exam_batch='期中', status=1,
        ))
        db.session.commit()

    before = client.get('/api/scores/my', headers=auth(student)).get_json()['data']
    assert before['scores'] == []
    assert client.get('/api/stats/my-trend', headers=auth(student)).get_json()['data']['series'] == []

    created = client.post('/api/exam-publish', headers=auth(admin), json={
        'exam_name': '期中发布', 'term': '2025-2026-2', 'exam_batch': '期中',
        'class_name': '2025级1班',
    }).get_json()['data']
    assert client.post(f"/api/exam-publish/{created['id']}/publish", headers=auth(admin), json={}).get_json()['code'] == 0

    after = client.get('/api/scores/my', headers=auth(student)).get_json()['data']
    assert len(after['scores']) == 1
    assert after['scores'][0]['course_id'] == 'MATH01'
    trend = client.get('/api/stats/my-trend?term=2025-2026-2', headers=auth(student)).get_json()['data']
    assert trend['series'][0]['exam_batch'] == '期中'

    assert client.post(f"/api/exam-publish/{created['id']}/withdraw", headers=auth(admin), json={}).get_json()['code'] == 0
    withdrawn = client.get('/api/scores/my', headers=auth(student)).get_json()['data']
    assert withdrawn['scores'] == []
    assert client.get('/api/stats/my-trend', headers=auth(student)).get_json()['data']['series'] == []
