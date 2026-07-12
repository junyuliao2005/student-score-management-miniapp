"""用户/课程/配置管理路由"""
from flask import Blueprint, request, g
from app.middleware.jwt_middleware import jwt_required
from app.middleware.permission_middleware import permission_required
from app.services import user_service, course_service, audit_service, teacher_scope_service
from app.services.config_loader import clear_cache
from app.models.sys_config import SysConfig
from app.models.role import Role
from app.extensions import db
from app.utils.response import success
from app.utils.validators import require_fields
from app.utils.errors import BusinessError, ErrorCode

config_bp = Blueprint('config', __name__)

SCORE_DISPLAY_DEFAULTS = [
    ('score_display.show_total', 'true', 'bool', '学生端显示总分'),
    ('score_display.show_rank', 'true', 'bool', '学生端显示排名'),
    ('score_display.show_class_stats', 'true', 'bool', '学生端显示班级统计'),
    ('score_display.show_warning', 'true', 'bool', '学生端显示预警提示'),
]


def ensure_score_display_configs():
    changed = False
    for key, value, config_type, remark in SCORE_DISPLAY_DEFAULTS:
        if not SysConfig.query.filter_by(config_key=key).first():
            db.session.add(SysConfig(
                config_key=key,
                config_value=value,
                config_type=config_type,
                scope='global',
                remark=remark,
            ))
            changed = True
    if changed:
        db.session.commit()
        clear_cache()


# ========== 用户管理 ==========

@config_bp.route('/api/users', methods=['GET'])
@jwt_required
@permission_required('user:manage')
def list_users():
    """分页查询用户"""
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)
    keyword = request.args.get('keyword')
    role_name = request.args.get('role_name')
    result = user_service.list_users(page, page_size, keyword, role_name)
    return success(result)


@config_bp.route('/api/users', methods=['POST'])
@jwt_required
@permission_required('user:manage')
def create_user():
    """新增用户"""
    data = request.get_json(force=True)
    require_fields(data, ['user_id', 'username', 'password', 'real_name'])

    result = user_service.create_user(
        user_id=data['user_id'],
        username=data['username'],
        password=data['password'],
        real_name=data['real_name'],
        class_name=data.get('class_name'),
        role_name=data.get('role_name', 'student'),
    )

    audit_service.write(
        action='user.create',
        operator_id=g.current_user['user_id'],
        target_type='user',
        target_id=data['user_id'],
        detail={'username': data['username']},
        trace_id=getattr(request, 'trace_id', ''),
    )

    return success(result)


@config_bp.route('/api/users/<user_id>', methods=['PUT'])
@jwt_required
@permission_required('user:manage')
def update_user(user_id):
    """修改用户"""
    data = request.get_json(force=True)
    result = user_service.update_user(user_id, **data)

    audit_service.write(
        action='user.update',
        operator_id=g.current_user['user_id'],
        target_type='user',
        target_id=user_id,
        detail=data,
        trace_id=getattr(request, 'trace_id', ''),
    )

    return success(result)


@config_bp.route('/api/classes', methods=['GET'])
@jwt_required
@permission_required('ai:class_overview')
def list_classes():
    """查询可用于班级分析的班级列表"""
    result = user_service.list_class_names()
    if teacher_scope_service.is_teacher(g.current_user) and not teacher_scope_service.is_admin(g.current_user):
        allowed = set(teacher_scope_service.get_scope(g.current_user)['class_names'])
        result['classes'] = [name for name in result.get('classes', []) if name in allowed]
    return success(result)


# ========== 课程管理 ==========

@config_bp.route('/api/courses', methods=['GET'])
@jwt_required
@permission_required('course:manage')
def list_courses():
    """分页查询课程"""
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)
    keyword = request.args.get('keyword')
    term = request.args.get('term')
    teacher_id = request.args.get('teacher_id')
    result = course_service.list_courses(page, page_size, keyword, term, teacher_id)
    return success(result)


@config_bp.route('/api/courses', methods=['POST'])
@jwt_required
@permission_required('course:manage')
def create_course():
    """新增课程"""
    data = request.get_json(force=True)
    require_fields(data, ['course_id', 'course_name', 'teacher_id', 'term'])

    result = course_service.create_course(
        course_id=data['course_id'],
        course_name=data['course_name'],
        teacher_id=data['teacher_id'],
        term=data['term'],
        credit=data.get('credit'),
    )

    audit_service.write(
        action='course.create',
        operator_id=g.current_user['user_id'],
        target_type='course',
        target_id=data['course_id'],
        detail={'course_name': data['course_name']},
        trace_id=getattr(request, 'trace_id', ''),
    )

    return success(result)


@config_bp.route('/api/courses/<course_id>', methods=['PUT'])
@jwt_required
@permission_required('course:manage')
def update_course(course_id):
    """修改课程"""
    data = request.get_json(force=True)
    result = course_service.update_course(course_id, **data)

    audit_service.write(
        action='course.update',
        operator_id=g.current_user['user_id'],
        target_type='course',
        target_id=course_id,
        detail=data,
        trace_id=getattr(request, 'trace_id', ''),
    )

    return success(result)


# ========== 系统配置管理 ==========

@config_bp.route('/api/configs', methods=['GET'])
@jwt_required
@permission_required('config:manage')
def list_configs():
    """查询所有配置"""
    ensure_score_display_configs()
    configs = SysConfig.query.order_by(SysConfig.config_key).all()
    return success([c.to_dict() for c in configs])


@config_bp.route('/api/configs/score-display', methods=['GET'])
@jwt_required
def get_score_display_config():
    """学生端成绩展示设置。"""
    ensure_score_display_configs()
    return success({
        'show_total': SysConfig.query.filter_by(config_key='score_display.show_total').first().config_value.lower() == 'true',
        'show_rank': SysConfig.query.filter_by(config_key='score_display.show_rank').first().config_value.lower() == 'true',
        'show_class_stats': SysConfig.query.filter_by(config_key='score_display.show_class_stats').first().config_value.lower() == 'true',
        'show_warning': SysConfig.query.filter_by(config_key='score_display.show_warning').first().config_value.lower() == 'true',
    })


@config_bp.route('/api/configs/<config_key>', methods=['PUT'])
@jwt_required
@permission_required('config:manage')
def update_config(config_key):
    """修改配置项"""
    data = request.get_json(force=True)
    config = SysConfig.query.filter_by(config_key=config_key).first()
    if not config:
        raise BusinessError(ErrorCode.CONFIG_MISSING, f'配置项不存在: {config_key}',
                            data={'config_key': config_key})

    if 'config_value' in data:
        config.config_value = str(data['config_value'])
    if 'remark' in data:
        config.remark = data['remark']

    db.session.commit()
    clear_cache()

    audit_service.write(
        action='config.update',
        operator_id=g.current_user['user_id'],
        target_type='config',
        target_id=config_key,
        detail=data,
        trace_id=getattr(request, 'trace_id', ''),
    )

    return success(config.to_dict())
