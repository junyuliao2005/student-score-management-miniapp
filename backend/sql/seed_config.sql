-- ============================================================
-- sys_config 初始数据
-- 插入默认配置项（使用 INSERT IGNORE 避免重复）
-- ============================================================

USE student_grade_db;

-- ========== 等级评定配置 ==========
INSERT IGNORE INTO sys_config (config_key, config_value, config_type, scope, remark)
VALUES ('grade.level.ranges',
        '{"优秀":[90,100],"良好":[80,89.99],"中等":[70,79.99],"及格":[60,69.99],"不及格":[0,59.99]}',
        'json', 'global', '等级分段区间');

INSERT IGNORE INTO sys_config (config_key, config_value, config_type, scope, remark)
VALUES ('comment.template.enabled', '1', 'int', 'global', '自动评语模板开关，1=启用');

-- ========== 预警配置 ==========
INSERT IGNORE INTO sys_config (config_key, config_value, config_type, scope, remark)
VALUES ('warning.low_score.threshold', '60', 'int', 'global', '低分预警阈值');

INSERT IGNORE INTO sys_config (config_key, config_value, config_type, scope, remark)
VALUES ('warning.subject_bias.delta', '20', 'int', 'global', '偏科预警阈值(最高分-最低分)');

INSERT IGNORE INTO sys_config (config_key, config_value, config_type, scope, remark)
VALUES ('warning.enabled', '1', 'int', 'global', '预警总开关，1=启用');

-- ========== AI 模块配置 ==========
INSERT IGNORE INTO sys_config (config_key, config_value, config_type, scope, remark)
VALUES ('ai.enabled', '1', 'int', 'global', 'AI模块总开关，1=启用');

INSERT IGNORE INTO sys_config (config_key, config_value, config_type, scope, remark)
VALUES ('ai.provider', 'mock', 'string', 'global', 'AI提供者: mock/openai_compatible');

INSERT IGNORE INTO sys_config (config_key, config_value, config_type, scope, remark)
VALUES ('ai.mock.enabled', '1', 'int', 'global', 'Mock模式开关，1=启用');

INSERT IGNORE INTO sys_config (config_key, config_value, config_type, scope, remark)
VALUES ('ai.max_input_chars', '6000', 'int', 'global', 'AI输入最大字符数');

INSERT IGNORE INTO sys_config (config_key, config_value, config_type, scope, remark)
VALUES ('ai.save_prompt', '0', 'int', 'global', '是否保存提示词到数据库，0=不保存');

INSERT IGNORE INTO sys_config (config_key, config_value, config_type, scope, remark)
VALUES ('ai.safety.enabled', '1', 'int', 'global', 'AI安全过滤开关，1=启用');

-- ========== RBAC 初始数据 ==========

-- 预置三个角色
INSERT IGNORE INTO roles (role_name, description) VALUES ('student', '学生');
INSERT IGNORE INTO roles (role_name, description) VALUES ('teacher', '教师');
INSERT IGNORE INTO roles (role_name, description) VALUES ('admin', '管理员');

-- 预置权限
INSERT IGNORE INTO permissions (permission_code, description) VALUES ('score:create', '录入成绩');
INSERT IGNORE INTO permissions (permission_code, description) VALUES ('score:update', '修改成绩');
INSERT IGNORE INTO permissions (permission_code, description) VALUES ('score:read:all', '查看所有成绩');
INSERT IGNORE INTO permissions (permission_code, description) VALUES ('score:read:self', '查看本人成绩');
INSERT IGNORE INTO permissions (permission_code, description) VALUES ('stats:read', '查看统计');
INSERT IGNORE INTO permissions (permission_code, description) VALUES ('stats:evaluate', '触发评定');
INSERT IGNORE INTO permissions (permission_code, description) VALUES ('warning:read', '查看预警');
INSERT IGNORE INTO permissions (permission_code, description) VALUES ('warning:refresh', '刷新预警');
INSERT IGNORE INTO permissions (permission_code, description) VALUES ('user:manage', '用户管理');
INSERT IGNORE INTO permissions (permission_code, description) VALUES ('course:manage', '课程管理');
INSERT IGNORE INTO permissions (permission_code, description) VALUES ('config:manage', '配置管理');
INSERT IGNORE INTO permissions (permission_code, description) VALUES ('role:manage', '角色管理');
INSERT IGNORE INTO permissions (permission_code, description) VALUES ('log:read', '日志查看');
INSERT IGNORE INTO permissions (permission_code, description) VALUES ('ai:student_advice:self', '查看本人AI学习建议');
INSERT IGNORE INTO permissions (permission_code, description) VALUES ('ai:student_advice:all', '查看任意学生AI建议');
INSERT IGNORE INTO permissions (permission_code, description) VALUES ('ai:class_overview', '班级学情分析');
INSERT IGNORE INTO permissions (permission_code, description) VALUES ('ai:exam_analyze', '试卷考点分析');
INSERT IGNORE INTO permissions (permission_code, description) VALUES ('ai:combined_advice', '成绩+试卷联合分析');
INSERT IGNORE INTO permissions (permission_code, description) VALUES ('ai:history:read', '查看AI分析历史');

-- 角色-权限映射: 学生
INSERT IGNORE INTO role_permission (role_id, permission_id)
SELECT r.role_id, p.permission_id FROM roles r, permissions p
WHERE r.role_name = 'student' AND p.permission_code IN (
    'score:read:self', 'ai:student_advice:self', 'ai:combined_advice', 'ai:history:read'
);

-- 角色-权限映射: 教师
INSERT IGNORE INTO role_permission (role_id, permission_id)
SELECT r.role_id, p.permission_id FROM roles r, permissions p
WHERE r.role_name = 'teacher' AND p.permission_code IN (
    'score:create', 'score:update', 'score:read:all',
    'stats:read', 'stats:evaluate',
    'warning:read', 'warning:refresh',
    'ai:student_advice:all', 'ai:class_overview', 'ai:exam_analyze',
    'ai:combined_advice', 'ai:history:read'
);

-- 角色-权限映射: 管理员（全部权限）
INSERT IGNORE INTO role_permission (role_id, permission_id)
SELECT r.role_id, p.permission_id FROM roles r, permissions p
WHERE r.role_name = 'admin';

-- ========== 演示账号 ==========
-- 密码均为 123456，使用 werkzeug pbkdf2:sha256 哈希
INSERT IGNORE INTO users (user_id, username, password_hash, real_name, class_name, status)
VALUES ('T001', 'teacher01', 'pbkdf2:sha256:600000$default$8b7d7f2e1a3c5d9e4f6b8a2c0d4e6f8a1b3c5d7e9f0a2b4c6d8e0f1a3b5c7d9', '张老师', NULL, 1);

INSERT IGNORE INTO users (user_id, username, password_hash, real_name, class_name, status)
VALUES ('T002', 'teacher02', 'pbkdf2:sha256:600000$default$8b7d7f2e1a3c5d9e4f6b8a2c0d4e6f8a1b3c5d7e9f0a2b4c6d8e0f1a3b5c7d9', '李老师', NULL, 1);

INSERT IGNORE INTO users (user_id, username, password_hash, real_name, class_name, status)
VALUES ('T003', 'teacher03', 'pbkdf2:sha256:600000$default$8b7d7f2e1a3c5d9e4f6b8a2c0d4e6f8a1b3c5d7e9f0a2b4c6d8e0f1a3b5c7d9', '王老师', NULL, 1);

INSERT IGNORE INTO users (user_id, username, password_hash, real_name, class_name, status)
VALUES ('A001', 'admin01', 'pbkdf2:sha256:600000$default$8b7d7f2e1a3c5d9e4f6b8a2c0d4e6f8a1b3c5d7e9f0a2b4c6d8e0f1a3b5c7d9', '系统管理员', NULL, 1);

INSERT IGNORE INTO users (user_id, username, password_hash, real_name, class_name, status)
VALUES ('S001', 'student01', 'pbkdf2:sha256:600000$default$8b7d7f2e1a3c5d9e4f6b8a2c0d4e6f8a1b3c5d7e9f0a2b4c6d8e0f1a3b5c7d9', '赵一', '2025级1班', 1);

INSERT IGNORE INTO users (user_id, username, password_hash, real_name, class_name, status)
VALUES ('S002', 'student02', 'pbkdf2:sha256:600000$default$8b7d7f2e1a3c5d9e4f6b8a2c0d4e6f8a1b3c5d7e9f0a2b4c6d8e0f1a3b5c7d9', '钱二', '2025级1班', 1);

INSERT IGNORE INTO users (user_id, username, password_hash, real_name, class_name, status)
VALUES ('S003', 'student03', 'pbkdf2:sha256:600000$default$8b7d7f2e1a3c5d9e4f6b8a2c0d4e6f8a1b3c5d7e9f0a2b4c6d8e0f1a3b5c7d9', '孙三', '2025级1班', 1);

-- 分配角色
INSERT IGNORE INTO user_role (user_id, role_id)
SELECT 'T001', role_id FROM roles WHERE role_name = 'teacher';
INSERT IGNORE INTO user_role (user_id, role_id)
SELECT 'T002', role_id FROM roles WHERE role_name = 'teacher';
INSERT IGNORE INTO user_role (user_id, role_id)
SELECT 'T003', role_id FROM roles WHERE role_name = 'teacher';
INSERT IGNORE INTO user_role (user_id, role_id)
SELECT 'A001', role_id FROM roles WHERE role_name = 'admin';
INSERT IGNORE INTO user_role (user_id, role_id)
SELECT 'S001', role_id FROM roles WHERE role_name = 'student';
INSERT IGNORE INTO user_role (user_id, role_id)
SELECT 'S002', role_id FROM roles WHERE role_name = 'student';
INSERT IGNORE INTO user_role (user_id, role_id)
SELECT 'S003', role_id FROM roles WHERE role_name = 'student';
