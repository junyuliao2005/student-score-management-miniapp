"""Excel 成绩批量导入服务。"""
import json
import logging
import os
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from app.extensions import db
from app.models.course import Course
from app.models.score import Score
from app.models.user import User
from app.services import audit_service, score_service
from app.utils.errors import BusinessError, ErrorCode

logger = logging.getLogger(__name__)

HEADER_ALIASES = {
    'student_id': {'学号', 'student_id'},
    'student_name': {'姓名', 'student_name'},
    'course_id': {'课程编号', 'course_id'},
    'course_name': {'课程名称', 'course_name'},
    'score': {'分数', 'score'},
    'exam_date': {'考试日期', 'exam_date'},
    'exam_batch': {'考试批次', 'exam_batch'},
    'term': {'学期', 'term'},
}
REQUIRED_FIELDS = ['student_id', 'course_id', 'score', 'exam_date', 'exam_batch']


def preview_import(file_storage):
    """解析并校验 .xlsx 文件，不写入成绩表。"""
    _validate_file(file_storage)

    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, '缺少依赖 openpyxl，请先安装后端依赖') from exc

    try:
        workbook = load_workbook(file_storage.stream, read_only=True, data_only=True)
        sheet = workbook.active
    except Exception as exc:
        raise BusinessError(ErrorCode.SCORE_IMPORT_INVALID, 'Excel 文件解析失败，请确认文件格式为 .xlsx') from exc

    rows_iter = sheet.iter_rows(values_only=True)
    try:
        header_row = next(rows_iter)
    except StopIteration:
        raise BusinessError(ErrorCode.SCORE_IMPORT_INVALID, 'Excel 文件为空')

    header_map = _build_header_map(header_row)
    missing = [field for field in REQUIRED_FIELDS if field not in header_map]
    if missing:
        raise BusinessError(
            ErrorCode.SCORE_IMPORT_INVALID,
            f'缺少必填表头: {", ".join(missing)}'
        )

    rows = []
    seen_keys = set()
    total_rows = 0
    valid_rows = 0
    error_rows = 0
    duplicate_rows = 0

    for row_index, row_values in enumerate(rows_iter, start=2):
        if _is_empty_row(row_values):
            continue

        total_rows += 1
        row = _parse_row(row_index, row_values, header_map)
        _validate_row(row, seen_keys)

        if row['status'] == 'valid':
            valid_rows += 1
        elif row['status'] == 'duplicate':
            duplicate_rows += 1
        else:
            error_rows += 1

        rows.append(row)

    import_id = uuid.uuid4().hex
    result = {
        'import_id': import_id,
        'total_rows': total_rows,
        'valid_rows': valid_rows,
        'error_rows': error_rows,
        'duplicate_rows': duplicate_rows,
        'rows': rows,
    }
    _save_preview(import_id, result)
    return result


def confirm_import(import_id, operator_id, trace_id):
    """导入 preview 中合法且不重复的成绩。"""
    preview = _load_preview(import_id)
    rows = preview.get('rows') or []

    inserted_count = 0
    skipped_count = 0
    runtime_error_count = 0

    for row in rows:
        if row.get('status') != 'valid':
            if row.get('status') == 'duplicate':
                skipped_count += 1
            continue

        if _has_active_duplicate(row['student_id'], row['course_id'], row['exam_batch']):
            skipped_count += 1
            row['status'] = 'duplicate'
            row['errors'] = ['数据库中已存在同一学生、课程、批次的有效成绩']
            continue

        payload = {
            'student_id': row['student_id'],
            'course_id': row['course_id'],
            'score': row['score'],
            'exam_date': row['exam_date'],
            'exam_batch': row['exam_batch'],
        }

        try:
            score_service.create_score(payload, operator_id=operator_id, trace_id=trace_id)
            inserted_count += 1
        except BusinessError as exc:
            row['status'] = 'error'
            row['errors'] = [exc.message]
            if exc.code == ErrorCode.SCORE_DUPLICATE:
                skipped_count += 1
                row['status'] = 'duplicate'
            else:
                runtime_error_count += 1
            logger.warning('批量导入单行失败: row=%s, error=%s', row.get('row_no'), exc.message)

    original_error_count = preview.get('error_rows', 0)

    audit_service.write(
        action='score.import.confirm',
        operator_id=operator_id,
        target_type='score_import',
        target_id=import_id,
        detail={
            'inserted_count': inserted_count,
            'skipped_count': skipped_count,
            'error_count': original_error_count + runtime_error_count,
        },
        trace_id=trace_id,
    )
    db.session.commit()

    return {
        'import_id': import_id,
        'inserted_count': inserted_count,
        'skipped_count': skipped_count,
        'error_count': original_error_count + runtime_error_count,
        'task_status': 'done',
    }


def _validate_file(file_storage):
    if not file_storage:
        raise BusinessError(ErrorCode.SCORE_IMPORT_INVALID, '请上传 Excel 文件')

    filename = file_storage.filename or ''
    if not filename.lower().endswith('.xlsx'):
        raise BusinessError(ErrorCode.SCORE_IMPORT_INVALID, '仅支持 .xlsx 文件')


def _build_header_map(header_row):
    header_map = {}
    alias_to_field = {}
    for field, aliases in HEADER_ALIASES.items():
        for alias in aliases:
            alias_to_field[_normalize_header(alias)] = field

    for index, cell_value in enumerate(header_row):
        normalized = _normalize_header(cell_value)
        field = alias_to_field.get(normalized)
        if field and field not in header_map:
            header_map[field] = index

    return header_map


def _parse_row(row_no, row_values, header_map):
    row = {
        'row_no': row_no,
        'student_id': _get_cell(row_values, header_map, 'student_id'),
        'student_name': _get_cell(row_values, header_map, 'student_name'),
        'course_id': _get_cell(row_values, header_map, 'course_id'),
        'course_name': _get_cell(row_values, header_map, 'course_name'),
        'score': _get_cell(row_values, header_map, 'score'),
        'exam_date': _get_cell(row_values, header_map, 'exam_date'),
        'exam_batch': _get_cell(row_values, header_map, 'exam_batch'),
        'term': _get_cell(row_values, header_map, 'term'),
        'status': 'valid',
        'errors': [],
    }

    for key in ['student_id', 'student_name', 'course_id', 'course_name', 'exam_batch', 'term']:
        if row[key] is not None:
            row[key] = str(row[key]).strip()

    return row


def _validate_row(row, seen_keys):
    errors = []

    student_id = row.get('student_id') or ''
    course_id = row.get('course_id') or ''
    exam_batch = row.get('exam_batch') or ''

    if not student_id:
        errors.append('学号不能为空')
    if not course_id:
        errors.append('课程编号不能为空')
    if not exam_batch:
        errors.append('考试批次不能为空')

    score_value = _parse_score(row.get('score'), errors)
    if score_value is not None:
        row['score'] = float(score_value)

    exam_date = _parse_exam_date(row.get('exam_date'), errors)
    if exam_date is not None:
        row['exam_date'] = exam_date

    student = None
    if student_id:
        student = User.query.filter_by(user_id=student_id).first()
        if not student:
            errors.append('学号不存在')
        elif student.status != 1:
            errors.append('学生状态不是启用')
        elif not student.has_role('student'):
            errors.append('用户不是学生角色')
        elif row.get('student_name') and row['student_name'] != student.real_name:
            errors.append('姓名与学号不匹配')

    course = None
    if course_id:
        course = Course.query.filter_by(course_id=course_id).first()
        if not course:
            errors.append('课程编号不存在')
        elif course.status != 1:
            errors.append('课程已停用')
        else:
            if row.get('course_name') and row['course_name'] != course.course_name:
                errors.append('课程名称与课程编号不匹配')
            if row.get('term') and row['term'] != course.term:
                errors.append('学期与课程所属学期不匹配')

    key = (student_id, course_id, exam_batch)
    if all(key):
        if key in seen_keys:
            errors.append('Excel 文件内存在重复成绩')
        else:
            seen_keys.add(key)

    if errors:
        row['status'] = 'error'
        row['errors'] = errors
        return

    if _has_active_duplicate(student_id, course_id, exam_batch):
        row['status'] = 'duplicate'
        row['errors'] = ['数据库中已存在同一学生、课程、批次的有效成绩']
        return

    row['status'] = 'valid'
    row['errors'] = []


def _parse_score(value, errors):
    try:
        score = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError, AttributeError):
        errors.append('分数必须是数字')
        return None

    if score < 0 or score > 100:
        errors.append('分数必须在 0 到 100 之间')
        return None

    return score


def _parse_exam_date(value, errors):
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d')
    if isinstance(value, date):
        return value.strftime('%Y-%m-%d')

    try:
        parsed = datetime.strptime(str(value).strip(), '%Y-%m-%d')
        return parsed.strftime('%Y-%m-%d')
    except (ValueError, TypeError, AttributeError):
        errors.append('考试日期必须为 YYYY-MM-DD')
        return None


def _has_active_duplicate(student_id, course_id, exam_batch):
    return Score.query.filter_by(
        student_id=student_id,
        course_id=course_id,
        exam_batch=exam_batch,
        status=1,
    ).first() is not None


def _get_cell(row_values, header_map, field):
    index = header_map.get(field)
    if index is None or index >= len(row_values):
        return None
    return row_values[index]


def _normalize_header(value):
    return str(value or '').strip().lower()


def _is_empty_row(row_values):
    return all(value is None or str(value).strip() == '' for value in row_values)


def _preview_dir():
    backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(backend_root, '.tmp', 'score_imports')
    os.makedirs(path, exist_ok=True)
    return path


def _preview_path(import_id):
    safe_id = ''.join(ch for ch in import_id if ch.isalnum())
    return os.path.join(_preview_dir(), f'{safe_id}.json')


def _save_preview(import_id, data):
    with open(_preview_path(import_id), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load_preview(import_id):
    if not import_id:
        raise BusinessError(ErrorCode.SCORE_IMPORT_INVALID, 'import_id 不能为空')

    path = _preview_path(import_id)
    if not os.path.exists(path):
        raise BusinessError(ErrorCode.SCORE_IMPORT_INVALID, '导入预览结果不存在或已过期')

    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)
