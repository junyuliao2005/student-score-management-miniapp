import json

from app.extensions import db
from app.models.ai_analysis import AiAnalysis
from app.models.ai_feedback import AiAnalysisFeedback

from conftest import auth


def test_ai_history_visibility_and_feedback(app, client, login):
    student = login('student01')
    teacher = login('teacher01')
    with app.app_context():
        own_student = AiAnalysis(
            analysis_type='student_advice', target_id='S001',
            result_text=json.dumps({'summary': '学生建议'}), provider='mock', status='success',
            created_by='S001', trace_id='student-history',
        )
        teacher_record = AiAnalysis(
            analysis_type='class_overview', target_id='2025级1班',
            result_text=json.dumps({'summary': '班级分析'}), provider='mock', status='success',
            created_by='T001', trace_id='teacher-history',
        )
        db.session.add_all([own_student, teacher_record])
        db.session.commit()
        student_id = own_student.analysis_id
        teacher_id = teacher_record.analysis_id

    student_history = client.get('/api/ai/history', headers=auth(student)).get_json()['data']
    assert [item['analysis_id'] for item in student_history['list']] == [student_id]
    assert student_history['list'][0]['result']['summary'] == '学生建议'
    assert client.post(
        f'/api/ai/history/{student_id}/feedback', headers=auth(student), json={'rating': 'useful'},
    ).get_json()['code'] == 0
    assert client.post(
        f'/api/ai/history/{teacher_id}/feedback', headers=auth(student), json={'rating': 'useful'},
    ).status_code == 403
    assert client.post(
        f'/api/ai/history/{teacher_id}/feedback', headers=auth(teacher), json={'rating': 'not_useful'},
    ).get_json()['code'] == 0
    with app.app_context():
        assert AiAnalysisFeedback.query.count() == 2
