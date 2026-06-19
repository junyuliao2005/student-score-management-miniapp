"""
数据库初始化脚本
用法: cd backend && python scripts/init_db.py

功能:
1. 创建所有数据库表
2. 初始化 RBAC 数据（角色、权限、映射）
3. 初始化 sys_config 配置项
4. 创建演示账号（密码由 werkzeug 生成真实哈希）
"""

import sys
import os

# 将 backend 目录加入 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models import (
    User, Role, Permission, UserRole, RolePermission,
    Course, Score, SysConfig, AuditLog, AiAnalysis, ExamPaper,
)
from app.utils.hash_util import hash_password


def seed_roles_permissions(app):
    """初始化角色和权限"""
    # 角色
    roles_data = [
        ('student', '学生'),
        ('teacher', '教师'),
        ('admin', '管理员'),
    ]
    for name, desc in roles_data:
        if not Role.query.filter_by(role_name=name).first():
            db.session.add(Role(role_name=name, description=desc))

    # 权限
    permissions_data = [
        ('score:create', '录入成绩'),
        ('score:update', '修改成绩'),
        ('score:read:all', '查看所有成绩'),
        ('score:read:self', '查看本人成绩'),
        ('stats:read', '查看统计'),
        ('stats:evaluate', '触发评定'),
        ('warning:read', '查看预警'),
        ('warning:refresh', '刷新预警'),
        ('user:manage', '用户管理'),
        ('course:manage', '课程管理'),
        ('config:manage', '配置管理'),
        ('role:manage', '角色管理'),
        ('log:read', '日志查看'),
        ('ai:student_advice:self', '查看本人AI学习建议'),
        ('ai:student_advice:all', '查看任意学生AI建议'),
        ('ai:class_overview', '班级学情分析'),
        ('ai:exam_analyze', '试卷考点分析'),
        ('ai:combined_advice', '成绩+试卷联合分析'),
        ('ai:history:read', '查看AI分析历史'),
    ]
    for code, desc in permissions_data:
        if not Permission.query.filter_by(permission_code=code).first():
            db.session.add(Permission(permission_code=code, description=desc))

    db.session.flush()

    # 角色-权限映射
    role_perm_map = {
        'student': [
            'score:read:self', 'ai:student_advice:self',
            'ai:combined_advice', 'ai:history:read',
        ],
        'teacher': [
            'score:create', 'score:update', 'score:read:all',
            'stats:read', 'stats:evaluate',
            'warning:read', 'warning:refresh',
            'ai:student_advice:all', 'ai:class_overview', 'ai:exam_analyze',
            'ai:combined_advice', 'ai:history:read',
        ],
        'admin': None,  # None 表示全部权限
    }

    for role_name, perm_codes in role_perm_map.items():
        role = Role.query.filter_by(role_name=role_name).first()
        if not role:
            continue
        if perm_codes is None:
            perms = Permission.query.all()
        else:
            perms = Permission.query.filter(Permission.permission_code.in_(perm_codes)).all()
        for perm in perms:
            existing = RolePermission.query.filter_by(
                role_id=role.role_id, permission_id=perm.permission_id
            ).first()
            if not existing:
                db.session.add(RolePermission(role_id=role.role_id, permission_id=perm.permission_id))

    db.session.commit()
    print('[OK] 角色和权限初始化完成')


def seed_sys_config(app):
    """初始化系统配置"""
    configs = [
        ('grade.level.ranges',
         '{"优秀":[90,100],"良好":[80,89.99],"中等":[70,79.99],"及格":[60,69.99],"不及格":[0,59.99]}',
         'json', 'global', '等级分段区间'),
        ('comment.template.enabled', '1', 'int', 'global', '自动评语模板开关，1=启用'),
        ('warning.low_score.threshold', '60', 'int', 'global', '低分预警阈值'),
        ('warning.subject_bias.delta', '20', 'int', 'global', '偏科预警阈值(最高分-最低分)'),
        ('warning.enabled', '1', 'int', 'global', '预警总开关，1=启用'),
        ('ai.enabled', '1', 'int', 'global', 'AI模块总开关，1=启用'),
        ('ai.provider', 'mock', 'string', 'global', 'AI提供者: mock/openai_compatible'),
        ('ai.mock.enabled', '1', 'int', 'global', 'Mock模式开关，1=启用'),
        ('ai.max_input_chars', '6000', 'int', 'global', 'AI输入最大字符数'),
        ('ai.save_prompt', '0', 'int', 'global', '是否保存提示词到数据库，0=不保存'),
        ('ai.safety.enabled', '1', 'int', 'global', 'AI安全过滤开关，1=启用'),
    ]
    for key, value, type_, scope, remark in configs:
        existing = SysConfig.query.filter_by(config_key=key).first()
        if not existing:
            db.session.add(SysConfig(
                config_key=key, config_value=value, config_type=type_,
                scope=scope, remark=remark
            ))
    db.session.commit()
    print('[OK] 系统配置初始化完成')


def seed_demo_users(app):
    """创建演示账号"""
    default_pw = hash_password('123456')

    users_data = [
        ('T001', 'teacher01', '张老师', None, 'teacher'),
        ('T002', 'teacher02', '李老师', None, 'teacher'),
        ('T003', 'teacher03', '王老师', None, 'teacher'),
        ('A001', 'admin01', '系统管理员', None, 'admin'),
        ('S001', 'student01', '赵一', '2025级1班', 'student'),
        ('S002', 'student02', '钱二', '2025级1班', 'student'),
        ('S003', 'student03', '孙三', '2025级1班', 'student'),
        ('S004', 'student04', '李四', '2025级1班', 'student'),
        ('S005', 'student05', '周五', '2025级1班', 'student'),
        ('S006', 'student06', '吴六', '2025级1班', 'student'),
        ('S007', 'student07', '郑七', '2025级1班', 'student'),
        ('S008', 'student08', '王八', '2025级1班', 'student'),
        ('S009', 'student09', '冯九', '2025级1班', 'student'),
        ('S010', 'student10', '陈十', '2025级1班', 'student'),
    ]

    for uid, uname, rname, cls, role_name in users_data:
        user = User.query.filter_by(user_id=uid).first()
        if not user:
            user = User(
                user_id=uid, username=uname, password_hash=default_pw,
                real_name=rname, class_name=cls, status=1
            )
            db.session.add(user)
            db.session.flush()

        # 分配角色
        role = Role.query.filter_by(role_name=role_name).first()
        if role:
            existing = UserRole.query.filter_by(user_id=uid, role_id=role.role_id).first()
            if not existing:
                db.session.add(UserRole(user_id=uid, role_id=role.role_id))

    db.session.commit()
    print('[OK] 演示账号创建完成')


def main():
    app = create_app()
    with app.app_context():
        print('=' * 50)
        print('学生成绩管理小程序 - 数据库初始化')
        print('=' * 50)

        # 创建所有表
        db.create_all()
        print('[OK] 数据库表创建完成')

        # 初始化数据
        seed_roles_permissions(app)
        seed_sys_config(app)
        seed_demo_users(app)

        print('=' * 50)
        print('初始化完成！')
        print('')
        print('默认演示账号 (密码均为 123456):')
        print('  教师: teacher01 / T001')
        print('  学生: student01 / S001')
        print('  管理员: admin01 / A001')
        print('=' * 50)


if __name__ == '__main__':
    main()
