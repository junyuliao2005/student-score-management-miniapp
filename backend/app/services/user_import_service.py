"""Excel 学生基础信息批量导入服务。"""
import json
import logging
import os
import uuid

from app.extensions import db
from app.models.role import Role, UserRole
from app.models.user import User
from app.services import audit_service
from app.utils.errors import BusinessError, ErrorCode
from app.utils.hash_util import hash_password

logger = logging.getLogger(__name__)

HEADER_ALIASES = {
    'student_id': {'学号', 'student_id'},
    'real_name': {'姓名', 'real_name', 'student_name'},
    'class_name': {'班级', 'class_name'},
    'username': {'用户名', 'username'},
    'grade': {'年级', 'grade'},
    'school_name': {'学校', 'school_name'},
    'gender': {'性别', 'gender'},
    'phone': {'手机号', 'phone'},
    'password': {'初始密码', 'password'},
}
REQUIRED_FIELDS = ['student_id', 'real_name', 'class_name']
DEFAULT_PASSWORD = '123456'


def preview_import(file_storage):
    """解析并校验 .xlsx 学生基础信息文件，不写入 users 表。"""
    _validate_file(file_storage)

    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise BusinessError(ErrorCode.INTERNAL_SERVER_ERROR, '缺少依赖 openpyxl，请先安装后端依赖') from exc

    try:
        workbook = load_workbook(file_storage.stream, read_only=True, data_only=True)
        sheet = workbook.active
    except Exception as exc:
        raise BusinessError(ErrorCode.USER_IMPORT_INVALID, 'Excel 文件解析失败，请确认文件格式为 .xlsx') from exc

    rows_iter = sheet.iter_rows(values_only=True)
    try:
        header_row = next(rows_iter)
    except StopIteration:
        raise BusinessError(ErrorCode.USER_IMPORT_INVALID, 'Excel 文件为空')

    header_map = _build_header_map(header_row)
    missing = [field for field in REQUIRED_FIELDS if field not in header_map]
    if missing:
        raise BusinessError(
            ErrorCode.USER_IMPORT_INVALID,
            f'缺少必填表头: {", ".join(missing)}'
        )

    rows = []
    seen_student_ids = set()
    seen_usernames = set()
    total_rows = 0
    valid_rows = 0
    duplicate_rows = 0
    error_rows = 0

    for row_index, row_values in enumerate(rows_iter, start=2):
        if _is_empty_row(row_values):
            continue

        total_rows += 1
        row = _parse_row(row_index, row_values, header_map)
        _validate_row(row, seen_student_ids, seen_usernames)

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
        'duplicate_rows': duplicate_rows,
        'error_rows': error_rows,
        'rows': rows,
    }
    _save_preview(import_id, result)
    return _public_preview(result)


def confirm_import(import_id, operator_id, trace_id):
    """导入 preview 中合法且数据库未重复的学生账号。"""
    preview = _load_preview(import_id)
    rows = preview.get('rows') or []
    student_role = Role.query.filter_by(role_name='student').first()
    if not student_role:
        raise BusinessError(ErrorCode.ROLE_MAPPING_INVALID, '学生角色不存在，无法导入')

    inserted_count = 0
    skipped_count = 0
    runtime_error_count = 0

    for row in rows:
        if row.get('status') != 'valid':
            if row.get('status') == 'duplicate':
                skipped_count += 1
            continue

        student_id = row['student_id']
        username = row['username']
        if User.query.filter_by(user_id=student_id).first() or User.query.filter_by(username=username).first():
            skipped_count += 1
            row['status'] = 'duplicate'
            row['errors'] = ['学生或用户名已存在，已跳过']
            continue

        try:
            with db.session.begin_nested():
                user = User(
                    user_id=student_id,
                    username=username,
                    password_hash=hash_password(row.get('password') or DEFAULT_PASSWORD),
                    real_name=row['real_name'],
                    class_name=row['class_name'],
                    status=1,
                )
                db.session.add(user)
                db.session.flush()
                db.session.add(UserRole(user_id=student_id, role_id=student_role.role_id))
            inserted_count += 1
        except Exception as exc:
            runtime_error_count += 1
            row['status'] = 'error'
            row['errors'] = ['写入数据库失败']
            logger.exception('学生批量导入单行失败: row=%s, error=%s', row.get('row_no'), exc)

    audit_service.write(
        action='user.import.confirm',
        operator_id=operator_id,
        target_type='user_import',
        target_id=import_id,
        detail={
            'inserted_count': inserted_count,
            'skipped_count': skipped_count,
            'error_count': preview.get('error_rows', 0) + runtime_error_count,
        },
        trace_id=trace_id,
    )
    db.session.commit()

    return {
        'import_id': import_id,
        'inserted_count': inserted_count,
        'skipped_count': skipped_count,
        'error_count': preview.get('error_rows', 0) + runtime_error_count,
        'task_status': 'done',
    }


def _validate_file(file_storage):
    if not file_storage:
        raise BusinessError(ErrorCode.USER_IMPORT_INVALID, '请上传 Excel 文件')

    filename = file_storage.filename or ''
    if not filename.lower().endswith('.xlsx'):
        raise BusinessError(ErrorCode.USER_IMPORT_INVALID, '仅支持 .xlsx 文件')


def _build_header_map(header_row):
    header_map = {}
    alias_to_field = {}
    for field, aliases in HEADER_ALIASES.items():
        for alias in aliases:
            alias_to_field[_normalize_header(alias)] = field

    for index, cell_value in enumerate(header_row):
        field = alias_to_field.get(_normalize_header(cell_value))
        if field and field not in header_map:
            header_map[field] = index

    return header_map


def _parse_row(row_no, row_values, header_map):
    row = {
        'row_no': row_no,
        'student_id': _get_cell(row_values, header_map, 'student_id'),
        'username': _get_cell(row_values, header_map, 'username'),
        'real_name': _get_cell(row_values, header_map, 'real_name'),
        'class_name': _get_cell(row_values, header_map, 'class_name'),
        'grade': _get_cell(row_values, header_map, 'grade'),
        'school_name': _get_cell(row_values, header_map, 'school_name'),
        'gender': _get_cell(row_values, header_map, 'gender'),
        'phone': _get_cell(row_values, header_map, 'phone'),
        'password': _get_cell(row_values, header_map, 'password'),
        'role': 'student',
        'status_value': 1,
        'status': 'valid',
        'errors': [],
    }

    for key in ['student_id', 'username', 'real_name', 'class_name', 'grade',
                'school_name', 'gender', 'phone', 'password']:
        if row[key] is not None:
            row[key] = str(row[key]).strip()

    if not row['username'] and row['student_id']:
        row['username'] = row['student_id']
    if not row['password']:
        row['password'] = DEFAULT_PASSWORD

    return row


def _validate_row(row, seen_student_ids, seen_usernames):
    errors = []
    student_id = row.get('student_id') or ''
    username = row.get('username') or ''

    if not student_id:
        errors.append('学号不能为空')
    if not row.get('real_name'):
        errors.append('姓名不能为空')
    if not row.get('class_name'):
        errors.append('班级不能为空')
    if not username:
        errors.append('用户名不能为空')

    if student_id:
        if student_id in seen_student_ids:
            errors.append('Excel 文件内学号重复')
        else:
            seen_student_ids.add(student_id)

    if username:
        if username in seen_usernames:
            errors.append('Excel 文件内用户名重复')
        else:
            seen_usernames.add(username)

    if errors:
        row['status'] = 'error'
        row['errors'] = errors
        return

    if User.query.filter_by(user_id=student_id).first():
        row['status'] = 'duplicate'
        row['errors'] = ['学号已存在']
        return

    username_owner = User.query.filter_by(username=username).first()
    if username_owner:
        row['status'] = 'error'
        row['errors'] = ['用户名已存在']
        return

    row['status'] = 'valid'
    row['errors'] = []


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
    path = os.path.join(backend_root, '.tmp', 'user_imports')
    os.makedirs(path, exist_ok=True)
    return path


def _preview_path(import_id):
    safe_id = ''.join(ch for ch in str(import_id or '') if ch.isalnum())
    return os.path.join(_preview_dir(), f'{safe_id}.json')


def _save_preview(import_id, data):
    with open(_preview_path(import_id), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load_preview(import_id):
    if not import_id:
        raise BusinessError(ErrorCode.USER_IMPORT_INVALID, 'import_id 不能为空')

    path = _preview_path(import_id)
    if not os.path.exists(path):
        raise BusinessError(ErrorCode.USER_IMPORT_INVALID, '导入预览结果不存在或已过期')

    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _public_preview(data):
    public = dict(data)
    public['rows'] = []
    for row in data.get('rows') or []:
        public_row = dict(row)
        public_row.pop('password', None)
        public['rows'].append(public_row)
    return public
