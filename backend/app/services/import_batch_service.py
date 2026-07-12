"""Atomic import ledger and conservative, non-destructive rollback."""
import json
import re
import uuid
from datetime import date, datetime

from app.extensions import db
from app.models.ai_analysis import AiAnalysis
from app.models.course import Course
from app.models.exam_publish import ExamPublishSetting, ParentScoreConfirmation, ParentStudentBinding
from app.models.import_batch import ImportBatch, ImportBatchEntry
from app.models.message import Message
from app.models.score import Score
from app.models.teacher_binding import TeacherClassBinding, TeacherCourseBinding
from app.models.user import User
from app.services import audit_service
from app.utils.errors import BusinessError, ErrorCode
from app.utils.validators import validate_pagination


SENSITIVE_KEYS = {
    'password', 'password_hash', 'token', 'jwt', 'api_key', 'authorization',
    'openid', 'secret_key', 'db_password',
}


def create_batch(import_type, operator_user_id, source_filename, total_rows, metadata=None):
    batch = ImportBatch(
        import_batch_id=str(uuid.uuid4()),
        import_type=str(import_type),
        operator_user_id=operator_user_id,
        source_filename=_safe_filename(source_filename),
        status='processing',
        total_rows=max(int(total_rows or 0), 0),
        metadata_json=_dump_safe_json(metadata or {}),
    )
    db.session.add(batch)
    db.session.flush()
    return batch


def record_score_entry(batch, score, row_number=None, action_type='create', before=None):
    _record_entry(
        batch=batch,
        entity_type='score',
        entity_id=str(score.score_id),
        action_type=action_type,
        before=before,
        after=score_snapshot(score),
        row_number=row_number,
    )


def record_user_entry(batch, user, row_number=None):
    _record_entry(
        batch=batch,
        entity_type='user',
        entity_id=user.user_id,
        action_type='create',
        before=None,
        after=user_snapshot(user),
        row_number=row_number,
    )


def complete_batch(batch, success_rows, failed_rows):
    batch.success_rows = max(int(success_rows or 0), 0)
    batch.failed_rows = max(int(failed_rows or 0), 0)
    batch.status = 'completed'
    batch.completed_at = datetime.now()
    db.session.flush()


def list_batches(page=1, page_size=20, import_type=None, status=None, operator_user_id=None):
    page, page_size = validate_pagination({'page': page, 'page_size': page_size})
    query = ImportBatch.query
    if import_type:
        query = query.filter(ImportBatch.import_type == import_type)
    if status:
        query = query.filter(ImportBatch.status == status)
    if operator_user_id:
        query = query.filter(ImportBatch.operator_user_id == operator_user_id)
    total = query.count()
    batches = query.order_by(ImportBatch.created_at.desc()) \
        .offset((page - 1) * page_size).limit(page_size).all()
    return {
        'list': [batch.to_dict() for batch in batches],
        'page': page,
        'page_size': page_size,
        'total': total,
        'total_pages': (total + page_size - 1) // page_size,
        'filter_options': {
            'import_types': [row[0] for row in db.session.query(ImportBatch.import_type).distinct().order_by(ImportBatch.import_type).all()],
            'statuses': [row[0] for row in db.session.query(ImportBatch.status).distinct().order_by(ImportBatch.status).all()],
        },
    }


def get_batch(import_batch_id):
    batch = _get_completed_or_visible_batch(import_batch_id)
    entries = ImportBatchEntry.query.filter_by(import_batch_id=import_batch_id) \
        .order_by(ImportBatchEntry.id).all()
    return {
        **batch.to_dict(),
        'metadata': _safe_json_object(batch.metadata_json),
        'rollback_summary': _safe_json_object(batch.rollback_summary),
        'entries': [_entry_public_dict(entry) for entry in entries],
    }


def rollback_batch(import_batch_id, operator_user_id, trace_id=''):
    batch = ImportBatch.query.filter_by(import_batch_id=import_batch_id).first()
    if not batch:
        raise BusinessError(ErrorCode.PERMISSION_DENIED, '导入批次不存在')
    if batch.status in ('rolled_back', 'rollback_partial'):
        raise BusinessError(ErrorCode.PERMISSION_DENIED, '该导入批次已经撤销，不能重复执行')
    if batch.status != 'completed':
        raise BusinessError(ErrorCode.PERMISSION_DENIED, '只有已完成批次可以执行撤销')

    entries = ImportBatchEntry.query.filter_by(import_batch_id=import_batch_id) \
        .order_by(ImportBatchEntry.id.desc()).all()
    success_count = 0
    skipped_count = 0
    failed_count = 0
    try:
        for entry in entries:
            try:
                with db.session.begin_nested():
                    success, reason = _rollback_entry(entry, operator_user_id)
                entry.rollback_status = 'rolled_back' if success else 'skipped'
                entry.rollback_reason = reason
                success_count += 1 if success else 0
                skipped_count += 0 if success else 1
            except Exception as exc:
                entry.rollback_status = 'failed'
                entry.rollback_reason = '撤销处理失败，未修改该记录'
                failed_count += 1

        batch.status = 'rolled_back' if skipped_count == 0 and failed_count == 0 else 'rollback_partial'
        batch.rolled_back_at = datetime.now()
        batch.rollback_operator_user_id = operator_user_id
        summary = {
            'success_count': success_count,
            'skipped_count': skipped_count,
            'failed_count': failed_count,
        }
        batch.rollback_summary = _dump_safe_json(summary)
        audit_service.write(
            action='import_batch.rollback',
            operator_id=operator_user_id,
            target_type='import_batch',
            target_id=import_batch_id,
            detail={'import_type': batch.import_type, **summary},
            trace_id=trace_id,
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return {**batch.to_dict(), **summary, 'entries': [_entry_public_dict(entry) for entry in entries]}


def score_snapshot(score):
    return {
        'student_id': score.student_id,
        'course_id': score.course_id,
        'score': float(score.score),
        'exam_date': score.exam_date.isoformat() if score.exam_date else None,
        'exam_batch': score.exam_batch,
        'status': int(score.status),
    }


def user_snapshot(user):
    return {
        'username': user.username,
        'real_name': user.real_name,
        'class_name': user.class_name,
        'status': int(user.status),
    }


def _record_entry(batch, entity_type, entity_id, action_type, before, after, row_number):
    if action_type not in ('create', 'update'):
        raise BusinessError(ErrorCode.PERMISSION_DENIED, '不支持的导入动作')
    entry = ImportBatchEntry(
        import_batch_id=batch.import_batch_id,
        entity_type=entity_type,
        entity_id=str(entity_id),
        action_type=action_type,
        before_snapshot=_dump_safe_json(before) if before is not None else None,
        after_snapshot=_dump_safe_json(after),
        row_number=int(row_number) if row_number is not None else None,
    )
    db.session.add(entry)
    db.session.flush()
    return entry


def _rollback_entry(entry, operator_user_id):
    before = _safe_json_object(entry.before_snapshot)
    after = _safe_json_object(entry.after_snapshot)
    if entry.entity_type == 'score':
        return _rollback_score(entry, before, after)
    if entry.entity_type == 'user':
        return _rollback_user(entry, after, operator_user_id)
    return False, '未知实体类型，未自动撤销'


def _rollback_score(entry, before, after):
    score = Score.query.filter_by(score_id=int(entry.entity_id)).first()
    if not score:
        return False, '成绩记录不存在'
    if score_snapshot(score) != after:
        return False, '成绩在导入后已被人工修改，未覆盖新数据'
    if entry.action_type == 'update':
        if not before:
            return False, '更新记录缺少导入前快照'
        score.score = before['score']
        score.exam_date = _parse_date(before.get('exam_date'))
        score.exam_batch = before['exam_batch']
        score.status = int(before.get('status', 1))
        score.stat_version = 0
        return True, '已恢复导入前成绩'

    conflict = Score.query.filter(
        Score.score_id != score.score_id,
        Score.student_id == score.student_id,
        Score.course_id == score.course_id,
        Score.exam_batch == score.exam_batch,
        Score.status == 0,
    ).first()
    if conflict:
        return False, '存在同组合历史删除记录，未自动逻辑删除'
    score.status = 0
    score.stat_version = 0
    return True, '已逻辑删除本批次新增成绩'


def _rollback_user(entry, after, operator_user_id):
    if entry.action_type != 'create':
        return False, '用户更新不支持自动撤销'
    user = User.query.filter_by(user_id=entry.entity_id).first()
    if not user:
        return False, '用户记录不存在'
    if user.user_id == operator_user_id or user.has_role('admin'):
        return False, '管理员账号或当前操作者不能被停用'
    if user_snapshot(user) != after:
        return False, '用户在导入后已被修改，未自动停用'
    if _user_has_references(user.user_id):
        return False, '用户已有成绩、课程、绑定、确认、留言或其他业务引用'
    user.status = 0
    return True, '已安全停用本批次新增用户'


def _user_has_references(user_id):
    checks = [
        db.session.query(Score.score_id).filter(Score.student_id == user_id).first(),
        db.session.query(Course.course_id).filter(Course.teacher_id == user_id).first(),
        db.session.query(Message.message_id).filter(
            db.or_(Message.sender_id == user_id, Message.receiver_id == user_id)
        ).first(),
        db.session.query(ParentStudentBinding.id).filter(
            db.or_(ParentStudentBinding.parent_user_id == user_id, ParentStudentBinding.student_user_id == user_id)
        ).first(),
        db.session.query(ParentScoreConfirmation.id).filter(
            db.or_(
                ParentScoreConfirmation.parent_user_id == user_id,
                ParentScoreConfirmation.student_user_id == user_id,
            )
        ).first(),
        db.session.query(TeacherClassBinding.binding_id).filter(TeacherClassBinding.teacher_id == user_id).first(),
        db.session.query(TeacherCourseBinding.binding_id).filter(TeacherCourseBinding.teacher_id == user_id).first(),
        db.session.query(ExamPublishSetting.id).filter(ExamPublishSetting.created_by == user_id).first(),
        db.session.query(AiAnalysis.analysis_id).filter(AiAnalysis.target_id == user_id).first(),
    ]
    return any(checks)


def _get_completed_or_visible_batch(import_batch_id):
    batch = ImportBatch.query.filter_by(import_batch_id=import_batch_id).first()
    if not batch:
        raise BusinessError(ErrorCode.PERMISSION_DENIED, '导入批次不存在')
    return batch


def _entry_public_dict(entry):
    data = entry.to_dict(include_snapshots=False)
    data['before_snapshot'] = _safe_json_object(entry.before_snapshot)
    data['after_snapshot'] = _safe_json_object(entry.after_snapshot)
    return data


def _dump_safe_json(value):
    sanitized = _sanitize(value)
    return json.dumps(sanitized, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def _safe_json_object(value):
    if not value:
        return None
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
    except (TypeError, ValueError):
        return None
    return _sanitize(parsed)


def _sanitize(value):
    if isinstance(value, dict):
        return {
            str(key): _sanitize(item)
            for key, item in value.items()
            if not _is_sensitive_key(key)
        }
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _is_sensitive_key(key):
    normalized = re.sub(r'[^a-z0-9]', '', str(key).strip().lower())
    return any(re.sub(r'[^a-z0-9]', '', token) in normalized for token in SENSITIVE_KEYS)


def _safe_filename(value):
    text = str(value or '').replace('\\', '/').rsplit('/', 1)[-1].strip()
    return text[:255] or None


def _parse_date(value):
    return datetime.strptime(str(value), '%Y-%m-%d').date()
