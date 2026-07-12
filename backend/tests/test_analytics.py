from datetime import date

from app.extensions import db
from app.models.course import Course
from app.models.score import Score

from conftest import auth


def _seed_analytics(app):
    with app.app_context():
        db.session.add_all([
            Course(course_id='MATH01', course_name='数学', teacher_id='T001', term='2025-2026-2', status=1),
            Course(course_id='ENG01', course_name='英语', teacher_id='T001', term='2025-2026-2', status=1),
        ])
        scores = [
            ('S001', 'MATH01', 70, '月考', date(2026, 3, 1)),
            ('S001', 'ENG01', 60, '月考', date(2026, 3, 1)),
            ('S001', 'MATH01', 90, '期中', date(2026, 4, 1)),
            ('S001', 'ENG01', 70, '期中', date(2026, 4, 1)),
            ('S002', 'MATH01', 80, '月考', date(2026, 3, 1)),
            ('S002', 'ENG01', 80, '月考', date(2026, 3, 1)),
            ('S002', 'MATH01', 85, '期中', date(2026, 4, 1)),
            ('S002', 'ENG01', 85, '期中', date(2026, 4, 1)),
        ]
        db.session.add_all([
            Score(student_id=sid, course_id=cid, score=value, exam_date=exam_date,
                  exam_batch=batch, status=1)
            for sid, cid, value, batch, exam_date in scores
        ])
        db.session.commit()


def test_lazy_analytics_endpoints_respect_teacher_scope(app, client, login):
    admin = login('admin01')
    teacher = login('teacher01')
    _seed_analytics(app)
    saved = client.put('/api/admin/teacher-bindings/T001', headers=auth(admin), json={
        'class_names': ['2025级1班'], 'course_ids': ['MATH01', 'ENG01'],
    })
    assert saved.get_json()['code'] == 0

    base = 'term=2025-2026-2&class_name=2025级1班'
    trend = client.get(f'/api/stats/trends?{base}', headers=auth(teacher)).get_json()['data']
    assert [item['exam_batch'] for item in trend['series']] == ['月考', '期中']

    distribution = client.get(
        f'/api/stats/distribution?{base}&exam_batch=期中', headers=auth(teacher),
    ).get_json()['data']
    assert distribution['total'] == 4
    assert sum(item['count'] for item in distribution['segments']) == 4

    progress = client.get(
        f'/api/stats/progress-rankings?{base}&baseline_batch=月考&current_batch=期中',
        headers=auth(teacher),
    ).get_json()['data']
    assert progress['list'][0]['student_id'] == 'S001'
    assert progress['list'][0]['delta'] == 15.0

    bias = client.get(
        f'/api/stats/bias-analysis?{base}&exam_batch=期中', headers=auth(teacher),
    ).get_json()['data']
    s001 = next(item for item in bias['list'] if item['student_id'] == 'S001')
    assert s001['gap'] == 20.0

    denied = client.get(
        '/api/stats/distribution?term=2025-2026-2&class_name=2025级2班&exam_batch=期中',
        headers=auth(teacher),
    ).get_json()['data']
    assert denied['total'] == 0


def test_heavy_analytics_require_explicit_batches(client, login):
    teacher = login('teacher01')
    distribution = client.get('/api/stats/distribution?term=2025-2026-2', headers=auth(teacher))
    progress = client.get('/api/stats/progress-rankings?term=2025-2026-2', headers=auth(teacher))
    bias = client.get('/api/stats/bias-analysis?term=2025-2026-2', headers=auth(teacher))
    assert distribution.status_code == 400
    assert progress.status_code == 400
    assert bias.status_code == 400
