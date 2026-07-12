"""成绩发布、家长绑定与签名确认服务。"""
from datetime import datetime
import base64
import io

from flask import current_app

from app.extensions import db
from app.models.course import Course
from app.models.exam_publish import (
    ExamPublishSetting,
    ParentScoreConfirmation,
    ParentStudentBinding,
)
from app.models.role import Role
from app.models.score import Score
from app.models.user import User
from app.services import audit_service, teacher_scope_service
from app.utils.errors import BusinessError, ErrorCode
from app.utils.validators import validate_pagination


EDITABLE_FIELDS = [
    'exam_name', 'term', 'exam_batch', 'grade_name', 'class_name',
    'show_total', 'show_rank', 'show_grade_rank', 'show_class_average',
    'show_subject_scores', 'require_parent_signature',
]


def list_publish_settings(filters, page=1, page_size=20, current_user=None):
    page, page_size = validate_pagination({'page': page, 'page_size': page_size})
    query = ExamPublishSetting.query
    if current_user and _is_teacher_only(current_user):
        query = query.filter(ExamPublishSetting.created_by == current_user.get('user_id'))
    for field in ('term', 'exam_batch', 'grade_name', 'class_name', 'status'):
        if filters.get(field):
            query = query.filter(getattr(ExamPublishSetting, field) == filters[field])
    total = query.count()
    items = query.order_by(ExamPublishSetting.created_at.desc()) \
        .offset((page - 1) * page_size).limit(page_size).all()
    result_items = []
    for item in items:
        data = item.to_dict()
        data.update(_match_counts_for_setting(item))
        result_items.append(data)
    return {
        'list': result_items,
        'page': page,
        'page_size': page_size,
        'total': total,
        'total_pages': (total + page_size - 1) // page_size,
    }


def create_publish_setting(payload, current_user, trace_id=''):
    _require_staff(current_user)
    _require_fields(payload, ['exam_name', 'term', 'exam_batch'])
    setting = ExamPublishSetting(created_by=current_user.get('user_id'), status='draft')
    _assign_setting_fields(setting, payload)
    _ensure_setting_scope(setting, current_user)
    db.session.add(setting)
    db.session.flush()
    audit_service.write(
        action='exam_publish.create',
        operator_id=current_user.get('user_id'),
        target_type='exam_publish',
        target_id=setting.id,
        detail=_audit_setting_detail(setting, current_user),
        trace_id=trace_id,
    )
    db.session.commit()
    return setting.to_dict()


def update_publish_setting(setting_id, payload, current_user, trace_id=''):
    _require_staff(current_user)
    setting = _get_setting(setting_id)
    _ensure_setting_scope(setting, current_user)
    if setting.status == 'published':
        raise BusinessError(ErrorCode.PERMISSION_DENIED, '已发布设置请先撤回后再编辑')
    _assign_setting_fields(setting, payload)
    _ensure_setting_scope(setting, current_user)
    audit_service.write(
        action='exam_publish.update',
        operator_id=current_user.get('user_id'),
        target_type='exam_publish',
        target_id=setting.id,
        detail=_audit_setting_detail(setting, current_user),
        trace_id=trace_id,
    )
    db.session.commit()
    return setting.to_dict()


def delete_publish_setting(setting_id, current_user, trace_id=''):
    _require_staff(current_user)
    setting = _get_setting(setting_id)
    _ensure_setting_scope(setting, current_user)
    if setting.status == 'published':
        raise BusinessError(ErrorCode.PERMISSION_DENIED, '请先撤回后再删除')
    if _is_teacher_only(current_user) and setting.created_by and setting.created_by != current_user.get('user_id'):
        raise BusinessError(ErrorCode.PERMISSION_DENIED, '只能删除自己创建的发布记录')

    ParentScoreConfirmation.query.filter_by(publish_id=setting.id).delete(synchronize_session=False)
    audit_service.write(
        action='exam_publish.delete',
        operator_id=current_user.get('user_id'),
        target_type='exam_publish',
        target_id=setting.id,
        detail=_audit_setting_detail(setting, current_user),
        trace_id=trace_id,
    )
    db.session.delete(setting)
    db.session.commit()
    return {'deleted': True, 'id': setting_id}


def publish_setting(setting_id, current_user, trace_id=''):
    _require_staff(current_user)
    setting = _get_setting(setting_id)
    _ensure_setting_scope(setting, current_user)
    setting.status = 'published'
    setting.publish_time = datetime.now()
    setting.withdraw_time = None
    created = 0
    if setting.require_parent_signature:
        created = _ensure_confirmations_for_setting(setting)
    audit_service.write(
        action='exam_publish.publish',
        operator_id=current_user.get('user_id'),
        target_type='exam_publish',
        target_id=setting.id,
        detail={**_audit_setting_detail(setting, current_user), 'created_confirmations': created},
        trace_id=trace_id,
    )
    db.session.commit()
    result = setting.to_dict()
    result['created_confirmations'] = created
    return result


def withdraw_setting(setting_id, current_user, trace_id=''):
    _require_staff(current_user)
    setting = _get_setting(setting_id)
    _ensure_setting_scope(setting, current_user)
    setting.status = 'withdrawn'
    setting.withdraw_time = datetime.now()
    audit_service.write(
        action='exam_publish.withdraw',
        operator_id=current_user.get('user_id'),
        target_type='exam_publish',
        target_id=setting.id,
        detail=_audit_setting_detail(setting, current_user),
        trace_id=trace_id,
    )
    db.session.commit()
    return setting.to_dict()


def list_confirmations(setting_id, current_user, filters=None):
    _require_staff(current_user)
    setting = _get_setting(setting_id)
    _ensure_setting_scope(setting, current_user)
    if setting.require_parent_signature:
        _ensure_confirmations_for_setting(setting)
        db.session.commit()

    filters = filters or {}
    query = db.session.query(
        ParentScoreConfirmation,
        User.real_name.label('parent_name'),
        User.user_id.label('parent_id'),
    ).join(
        User, ParentScoreConfirmation.parent_user_id == User.user_id
    ).filter(ParentScoreConfirmation.publish_id == setting_id)

    if filters.get('status'):
        query = query.filter(ParentScoreConfirmation.confirm_status == filters['status'])

    rows = query.order_by(ParentScoreConfirmation.student_user_id, ParentScoreConfirmation.parent_user_id).all()
    student_ids = [row.ParentScoreConfirmation.student_user_id for row in rows]
    students = _student_map(student_ids)

    result = []
    teacher_classes = None
    if _is_teacher_only(current_user):
        teacher_classes = set(teacher_scope_service.get_scope(current_user)['class_names'])
    for row in rows:
        confirm = row.ParentScoreConfirmation
        student = students.get(confirm.student_user_id, {})
        if teacher_classes is not None and student.get('class_name') not in teacher_classes:
            continue
        if filters.get('class_name') and student.get('class_name') != filters['class_name']:
            continue
        data = confirm.to_dict()
        data.update({
            'student_name': student.get('real_name'),
            'class_name': student.get('class_name'),
            'parent_name': row.parent_name,
            'parent_user_id': row.parent_id,
        })
        result.append(data)

    confirmed_count = sum(1 for item in result if item['confirm_status'] == 'confirmed')
    return {
        'list': result,
        'confirmed_count': confirmed_count,
        'pending_count': len(result) - confirmed_count,
        'total': len(result),
    }


def export_confirmations(setting_id, current_user):
    setting = _get_setting(setting_id)
    _ensure_setting_scope(setting, current_user)
    data = list_confirmations(setting_id, current_user)
    try:
        from openpyxl import Workbook
    except ImportError as exc:
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, '缺少 openpyxl，无法导出确认表') from exc
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = '家长确认情况'
    sheet.append(['考试名称', '学期', '考试批次', '学号', '学生姓名', '班级', '家长ID', '家长姓名', '确认状态', '确认时间', '备注'])
    for item in data['list']:
        sheet.append([
            setting.exam_name, setting.term, setting.exam_batch,
            item.get('student_user_id'), item.get('student_name'), item.get('class_name'),
            item.get('parent_user_id'), item.get('parent_name'), item.get('confirm_status'),
            item.get('confirmed_at'), item.get('remark'),
        ])
    output = io.BytesIO()
    workbook.save(output)
    safe_name = f'parent-confirmations-{setting.id}.xlsx'
    return {
        'filename': safe_name,
        'mime_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'content_base64': base64.b64encode(output.getvalue()).decode('ascii'),
        'confirmed_count': data['confirmed_count'],
        'pending_count': data['pending_count'],
    }


def list_bindings(filters, current_user):
    _require_staff(current_user)
    teacher_classes = None
    if _is_teacher_only(current_user):
        teacher_classes = set(teacher_scope_service.get_scope(current_user)['class_names'])
    query = db.session.query(
        ParentStudentBinding,
        User.real_name.label('parent_name'),
        User.username.label('parent_username'),
    ).join(
        User, ParentStudentBinding.parent_user_id == User.user_id
    )
    if filters.get('parent_user_id'):
        query = query.filter(ParentStudentBinding.parent_user_id == filters['parent_user_id'])
    if filters.get('student_user_id'):
        query = query.filter(ParentStudentBinding.student_user_id == filters['student_user_id'])
    if filters.get('status') is not None:
        query = query.filter(ParentStudentBinding.status == int(filters['status']))

    rows = query.order_by(ParentStudentBinding.created_at.desc()).all()
    students = _student_map([row.ParentStudentBinding.student_user_id for row in rows])
    result = []
    for row in rows:
        binding = row.ParentStudentBinding
        data = binding.to_dict()
        student = students.get(binding.student_user_id, {})
        if teacher_classes is not None and student.get('class_name') not in teacher_classes:
            continue
        data.update({
            'parent_name': row.parent_name,
            'parent_username': row.parent_username,
            'student_name': student.get('real_name'),
            'student_username': student.get('username'),
            'class_name': student.get('class_name'),
        })
        result.append(data)
    return {'list': result, 'total': len(result)}


def create_binding(payload, current_user, trace_id=''):
    _require_admin(current_user)
    parent = _resolve_user(payload.get('parent_user_id'), payload.get('parent_username'))
    student = _resolve_user(payload.get('student_user_id'), payload.get('student_username'))
    if not _user_has_role(parent.user_id, 'parent'):
        raise BusinessError(ErrorCode.PERMISSION_DENIED, '绑定用户不是家长角色')
    if not _user_has_role(student.user_id, 'student'):
        raise BusinessError(ErrorCode.PERMISSION_DENIED, '被绑定用户不是学生角色')

    binding = ParentStudentBinding.query.filter_by(
        parent_user_id=parent.user_id,
        student_user_id=student.user_id,
    ).first()
    if not binding:
        binding = ParentStudentBinding(parent_user_id=parent.user_id, student_user_id=student.user_id)
        db.session.add(binding)
    binding.relation = payload.get('relation') or binding.relation or '家长'
    binding.status = 1
    db.session.flush()
    audit_service.write(
        action='parent_binding.create',
        operator_id=current_user.get('user_id'),
        target_type='parent_binding',
        target_id=binding.id,
        detail={
            'parent_user_id': binding.parent_user_id,
            'student_user_id': binding.student_user_id,
            'relation': binding.relation,
            'actor_role': ','.join(current_user.get('roles', [])),
        },
        trace_id=trace_id,
    )
    db.session.commit()
    return binding.to_dict()


def disable_binding(binding_id, current_user, trace_id=''):
    _require_admin(current_user)
    binding = ParentStudentBinding.query.filter_by(id=binding_id).first()
    if not binding:
        raise BusinessError(ErrorCode.STUDENT_NOT_FOUND, '绑定关系不存在')
    binding.status = 0
    audit_service.write(
        action='parent_binding.disable',
        operator_id=current_user.get('user_id'),
        target_type='parent_binding',
        target_id=binding.id,
        detail={
            'parent_user_id': binding.parent_user_id,
            'student_user_id': binding.student_user_id,
            'actor_role': ','.join(current_user.get('roles', [])),
        },
        trace_id=trace_id,
    )
    db.session.commit()
    return binding.to_dict()


def my_children(current_user):
    _require_parent(current_user)
    parent_id = current_user.get('user_id')
    rows = db.session.query(
        ParentStudentBinding,
        User.real_name,
        User.class_name,
        User.username,
    ).join(
        User, ParentStudentBinding.student_user_id == User.user_id
    ).filter(
        ParentStudentBinding.parent_user_id == parent_id,
        ParentStudentBinding.status == 1,
        User.status == 1,
    ).order_by(User.class_name, User.user_id).all()
    return {
        'children': [
            {
                'student_id': row.ParentStudentBinding.student_user_id,
                'student_name': row.real_name,
                'username': row.username,
                'class_name': row.class_name,
                'relation': row.ParentStudentBinding.relation,
            }
            for row in rows
        ]
    }


def parent_published_scores(student_id, current_user):
    _require_parent(current_user)
    parent_id = current_user.get('user_id')
    _ensure_binding(parent_id, student_id)
    student = _get_student(student_id)
    settings = get_published_settings_for_student(student_id)
    exams = []
    matched_score_count = 0
    for setting in settings:
        scores = _scores_for_setting(student_id, setting)
        _log_parent_score_debug(parent_id, student_id, setting, len(scores), student)
        if not scores:
            continue
        matched_score_count += len(scores)
        summary = _summary_for_scores(scores)
        class_average = _class_average_for_setting(setting) if setting.show_class_average else None
        confirmation = _get_or_create_confirmation(setting, parent_id, student_id)
        exams.append({
            'publish_id': setting.id,
            'exam_name': setting.exam_name,
            'term': setting.term,
            'exam_batch': setting.exam_batch,
            'publish_time': setting.publish_time.strftime('%Y-%m-%d %H:%M:%S') if setting.publish_time else None,
            'settings': _display_settings(setting),
            'scores': scores if setting.show_subject_scores else [],
            'summary': summary,
            'class_average': class_average,
            'require_parent_signature': bool(setting.require_parent_signature),
            'confirmation': confirmation.to_dict() if confirmation else None,
        })
    db.session.commit()
    message = ''
    if settings and matched_score_count == 0:
        message = '已有发布记录，但未匹配到该学生成绩，请检查学期、考试批次、年级、班级设置'
    return {
        'student': {
            'student_id': student.user_id,
            'student_name': student.real_name,
            'class_name': student.class_name,
        },
        'list': exams,
        'exams': exams,
        'has_published_settings': bool(settings),
        'matched_score_count': matched_score_count,
        'message': message,
    }


def confirm_score(publish_id, payload, current_user, trace_id=''):
    _require_parent(current_user)
    parent_id = current_user.get('user_id')
    student_id = payload.get('student_id')
    signature_text = str(payload.get('signature_text') or '').strip()
    if not student_id:
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, '请选择学生')
    if not signature_text:
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, '请输入家长姓名确认')
    _ensure_binding(parent_id, student_id)
    setting = _get_setting(publish_id)
    if setting.status != 'published':
        raise BusinessError(ErrorCode.PERMISSION_DENIED, '成绩未发布或已撤回')
    if not setting.require_parent_signature:
        raise BusinessError(ErrorCode.PERMISSION_DENIED, '该考试不需要家长签名确认')
    if not _matches_student(setting, _get_student(student_id)):
        raise BusinessError(ErrorCode.PERMISSION_DENIED, '该发布设置不适用于当前学生')

    confirmation = _get_or_create_confirmation(setting, parent_id, student_id)
    confirmation.confirm_status = 'confirmed'
    confirmation.signature_text = signature_text
    confirmation.remark = payload.get('remark') or None
    confirmation.confirmed_at = datetime.now()
    audit_service.write(
        action='parent_score.confirm',
        operator_id=parent_id,
        target_type='parent_score_confirmation',
        target_id=confirmation.id,
        detail={
            'publish_id': publish_id,
            'student_user_id': student_id,
            'confirm_status': confirmation.confirm_status,
            'actor_role': ','.join(current_user.get('roles', [])),
        },
        trace_id=trace_id,
    )
    db.session.commit()
    return confirmation.to_dict()


def get_published_settings_for_student(student_id, filters=None):
    filters = filters or {}
    student = _get_student(student_id)
    query = ExamPublishSetting.query.filter_by(status='published')
    if filters.get('term'):
        query = query.filter(db.func.trim(ExamPublishSetting.term) == _norm_text(filters['term']))
    if filters.get('exam_batch'):
        query = query.filter(db.func.trim(ExamPublishSetting.exam_batch) == _norm_text(filters['exam_batch']))
    settings = query.order_by(ExamPublishSetting.publish_time.desc(), ExamPublishSetting.id.desc()).all()
    return [setting for setting in settings if _matches_student(setting, student)]


def has_any_publish_settings():
    return db.session.query(ExamPublishSetting.id).first() is not None


def first_display_settings(settings):
    if not settings:
        return None
    return _display_settings(settings[0])


def _assign_setting_fields(setting, payload):
    for field in EDITABLE_FIELDS:
        if field in payload:
            value = payload[field]
            if field.startswith('show_') or field == 'require_parent_signature':
                value = 1 if _bool(value) else 0
            elif field in ('grade_name', 'class_name'):
                value = _normalize_scope_value(value)
            elif isinstance(value, str):
                value = value.strip() or None
            setattr(setting, field, value)
    if not setting.exam_name or not setting.term or not setting.exam_batch:
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, '考试名称、学期、考试批次不能为空')


def _require_fields(payload, fields):
    missing = [field for field in fields if not str(payload.get(field) or '').strip()]
    if missing:
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, f"缺少必填字段: {', '.join(missing)}")


def _ensure_setting_scope(setting, current_user):
    if not _is_teacher_only(current_user):
        return
    if setting.created_by and setting.created_by != current_user.get('user_id'):
        raise BusinessError(ErrorCode.PERMISSION_DENIED, '只能管理自己创建的考试发布')
    if not _normalize_scope_value(setting.class_name):
        raise BusinessError(ErrorCode.PERMISSION_DENIED, '教师发布考试时必须选择已绑定班级')
    teacher_scope_service.ensure_access(current_user, class_name=setting.class_name)


def _require_staff(current_user):
    roles = current_user.get('roles', [])
    if 'admin' not in roles and 'teacher' not in roles:
        raise BusinessError(ErrorCode.PERMISSION_DENIED, '无权限管理成绩发布')


def _is_teacher_only(current_user):
    roles = current_user.get('roles', [])
    return 'teacher' in roles and 'admin' not in roles


def _require_admin(current_user):
    if 'admin' not in current_user.get('roles', []):
        raise BusinessError(ErrorCode.PERMISSION_DENIED, '仅管理员可管理家长绑定')


def _require_parent(current_user):
    if 'parent' not in current_user.get('roles', []):
        raise BusinessError(ErrorCode.PERMISSION_DENIED, '仅家长可访问')


def _get_setting(setting_id):
    setting = ExamPublishSetting.query.filter_by(id=setting_id).first()
    if not setting:
        raise BusinessError(ErrorCode.STUDENT_NOT_FOUND, '发布设置不存在')
    return setting


def _get_student(student_id):
    student = db.session.query(User).filter(User.user_id == student_id, User.status == 1).first()
    if not student:
        raise BusinessError(ErrorCode.STUDENT_NOT_FOUND, '学生不存在')
    return student


def _resolve_user(user_id=None, username=None):
    query = User.query
    if user_id:
        user = query.filter_by(user_id=user_id).first()
    elif username:
        user = query.filter_by(username=username).first()
    else:
        user = None
    if not user or user.status != 1:
        raise BusinessError(ErrorCode.STUDENT_NOT_FOUND, '用户不存在或已停用')
    return user


def _ensure_binding(parent_id, student_id):
    binding = ParentStudentBinding.query.filter_by(
        parent_user_id=parent_id,
        student_user_id=student_id,
        status=1,
    ).first()
    if not binding:
        raise BusinessError(ErrorCode.PERMISSION_DENIED, '无权查看该学生')
    return binding


def _user_has_role(user_id, role_name):
    role = Role.query.filter_by(role_name=role_name).first()
    if not role:
        return False
    return db.session.query(User).filter(User.user_id == user_id, User.roles.any(Role.role_name == role_name)).first() is not None


def _ensure_confirmations_for_setting(setting):
    students = _students_for_setting(setting)
    if not students:
        return 0
    student_ids = [student.user_id for student in students]
    bindings = ParentStudentBinding.query.filter(
        ParentStudentBinding.student_user_id.in_(student_ids),
        ParentStudentBinding.status == 1,
    ).all()
    created = 0
    for binding in bindings:
        existing = ParentScoreConfirmation.query.filter_by(
            publish_id=setting.id,
            parent_user_id=binding.parent_user_id,
            student_user_id=binding.student_user_id,
        ).first()
        if not existing:
            db.session.add(ParentScoreConfirmation(
                publish_id=setting.id,
                parent_user_id=binding.parent_user_id,
                student_user_id=binding.student_user_id,
                confirm_status='pending',
            ))
            created += 1
    db.session.flush()
    return created


def _get_or_create_confirmation(setting, parent_id, student_id):
    if not setting.require_parent_signature:
        return None
    confirmation = ParentScoreConfirmation.query.filter_by(
        publish_id=setting.id,
        parent_user_id=parent_id,
        student_user_id=student_id,
    ).first()
    if not confirmation:
        confirmation = ParentScoreConfirmation(
            publish_id=setting.id,
            parent_user_id=parent_id,
            student_user_id=student_id,
            confirm_status='pending',
        )
        db.session.add(confirmation)
        db.session.flush()
    return confirmation


def _students_for_setting(setting):
    query = User.query.filter(User.status == 1, User.roles.any(Role.role_name == 'student'))
    class_name = _normalize_scope_value(setting.class_name)
    if class_name:
        query = query.filter(db.func.trim(User.class_name) == class_name)
    students = query.order_by(User.class_name, User.user_id).all()
    return [student for student in students if _matches_student(setting, student)]


def _matches_student(setting, student):
    setting_class = _normalize_scope_value(setting.class_name)
    student_class = _norm_text(student.class_name)
    if setting_class and student_class != setting_class:
        return False
    setting_grade = _normalize_scope_value(setting.grade_name)
    if setting_grade and _parse_grade_name(student.class_name) != setting_grade:
        return False
    return True


def _scores_for_setting(student_id, setting):
    rows = db.session.query(
        Score.score_id,
        Score.course_id,
        Course.course_name,
        Score.score,
        Score.exam_date,
        Score.exam_batch,
        Score.total_score,
        Score.avg_score,
        Score.rank_no,
        Score.level_tag,
        Score.comment_text,
    ).join(Course, Score.course_id == Course.course_id).filter(
        Score.student_id == student_id,
        Score.status == 1,
        db.func.trim(Course.term) == _norm_text(setting.term),
        db.func.trim(Score.exam_batch) == _norm_text(setting.exam_batch),
    ).order_by(Course.course_id).all()
    return [
        {
            'score_id': row.score_id,
            'course_id': row.course_id,
            'course_name': row.course_name,
            'score': float(row.score),
            'exam_date': row.exam_date.strftime('%Y-%m-%d') if row.exam_date else None,
            'exam_batch': row.exam_batch,
            'total_score': float(row.total_score) if row.total_score is not None else None,
            'avg_score': float(row.avg_score) if row.avg_score is not None else None,
            'rank_no': row.rank_no,
            'level_tag': row.level_tag,
            'comment_text': row.comment_text,
        }
        for row in rows
    ]


def _summary_for_scores(scores):
    values = [item['score'] for item in scores]
    total = round(sum(values), 2) if values else 0
    average = round(total / len(values), 2) if values else 0
    weak = min(scores, key=lambda x: x['score']) if scores else None
    return {
        'total_score': total,
        'average_score': average,
        'subject_count': len(values),
        'weak_subject_tip': f"{weak.get('course_name') or weak.get('course_id')} 相对薄弱，可优先复习" if weak else '',
        'comment_text': next((item.get('comment_text') for item in scores if item.get('comment_text')), ''),
    }


def _class_average_for_setting(setting):
    query = db.session.query(db.func.avg(Score.score)).join(
        Course, Score.course_id == Course.course_id
    ).join(
        User, Score.student_id == User.user_id
    ).filter(
        Score.status == 1,
        db.func.trim(Course.term) == _norm_text(setting.term),
        db.func.trim(Score.exam_batch) == _norm_text(setting.exam_batch),
    )
    class_name = _normalize_scope_value(setting.class_name)
    grade_name = _normalize_scope_value(setting.grade_name)
    if class_name:
        query = query.filter(db.func.trim(User.class_name) == class_name)
    if grade_name:
        query = query.filter(User.class_name.like(f'{grade_name}%'))
        rows = query.with_entities(Score.score, User.class_name).all()
        values = [float(row.score) for row in rows if _parse_grade_name(row.class_name) == grade_name]
        return round(sum(values) / len(values), 2) if values else None
    avg = query.scalar()
    return round(float(avg), 2) if avg is not None else None


def _display_settings(setting):
    return {
        'show_total': bool(setting.show_total),
        'show_rank': bool(setting.show_rank),
        'show_grade_rank': bool(setting.show_grade_rank),
        'show_class_average': bool(setting.show_class_average),
        'show_subject_scores': bool(setting.show_subject_scores),
    }


def _audit_setting_detail(setting, current_user):
    return {
        'exam_name': setting.exam_name,
        'term': setting.term,
        'exam_batch': setting.exam_batch,
        'grade_name': setting.grade_name,
        'class_name': setting.class_name,
        'status': setting.status,
        'created_by': setting.created_by,
        'actor_role': ','.join(current_user.get('roles', [])),
    }


def _student_map(student_ids):
    if not student_ids:
        return {}
    rows = db.session.query(User.user_id, User.username, User.real_name, User.class_name).filter(
        User.user_id.in_(list(set(student_ids)))
    ).all()
    return {
        row.user_id: {
            'username': row.username,
            'real_name': row.real_name,
            'class_name': row.class_name,
        }
        for row in rows
    }


def _parse_grade_name(class_name):
    text = str(class_name or '').strip()
    if not text:
        return '未知年级'
    for grade in ('初一', '初二', '初三', '高一', '高二', '高三'):
        if text.startswith(grade):
            return grade
    return '未知年级'


def _norm_text(value):
    return str(value or '').strip()


def _normalize_scope_value(value):
    text = _norm_text(value)
    if not text or text in ('全部', '全部年级', '全部班级', '不限', '不限制'):
        return None
    return text


def _match_counts_for_setting(setting):
    query = db.session.query(
        db.func.count(db.distinct(Score.student_id)).label('student_count'),
        db.func.count(Score.score_id).label('score_count'),
    ).join(
        Course, Score.course_id == Course.course_id
    ).join(
        User, Score.student_id == User.user_id
    ).filter(
        Score.status == 1,
        User.status == 1,
        db.func.trim(Course.term) == _norm_text(setting.term),
        db.func.trim(Score.exam_batch) == _norm_text(setting.exam_batch),
    )
    query = _apply_setting_student_scope(query, setting)
    row = query.first()
    confirm_row = db.session.query(
        db.func.sum(db.case((ParentScoreConfirmation.confirm_status == 'confirmed', 1), else_=0)).label('confirmed'),
        db.func.sum(db.case((ParentScoreConfirmation.confirm_status != 'confirmed', 1), else_=0)).label('pending'),
    ).filter(ParentScoreConfirmation.publish_id == setting.id).first()
    return {
        'matched_student_count': int(row.student_count or 0) if row else 0,
        'matched_score_count': int(row.score_count or 0) if row else 0,
        'confirmed_parent_count': int(confirm_row.confirmed or 0) if confirm_row else 0,
        'pending_parent_count': int(confirm_row.pending or 0) if confirm_row else 0,
    }


def _apply_setting_student_scope(query, setting):
    class_name = _normalize_scope_value(setting.class_name)
    grade_name = _normalize_scope_value(setting.grade_name)
    if class_name:
        query = query.filter(db.func.trim(User.class_name) == class_name)
    if grade_name:
        query = query.filter(User.class_name.like(f'{grade_name}%'))
    return query


def _log_parent_score_debug(parent_id, student_id, setting, matched_score_count, student):
    try:
        current_app.logger.info(
            '[parent scores debug] parent_user_id=%s student_id=%s publish_id=%s '
            'term=%s exam_batch=%s grade_name=%s class_name=%s student_class=%s '
            'matched_score_count=%s',
            parent_id,
            student_id,
            setting.id,
            setting.term,
            setting.exam_batch,
            setting.grade_name,
            setting.class_name,
            student.class_name,
            matched_score_count,
        )
    except RuntimeError:
        pass


def _bool(value):
    return str(value).lower() in ('1', 'true', 'yes', 'on')
