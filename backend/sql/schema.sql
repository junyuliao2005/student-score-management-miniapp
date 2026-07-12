-- ============================================================
-- 学生成绩管理小程序 + AI 学情诊断辅助系统
-- 数据库 DDL 脚本
-- 数据库: MySQL 8.0+ / InnoDB / utf8mb4
-- ============================================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS student_grade_db
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_general_ci;

USE student_grade_db;

-- ============================================================
-- 1. users 用户表
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    user_id         VARCHAR(20)     NOT NULL,
    username        VARCHAR(50)     NOT NULL,
    password_hash   VARCHAR(128)    NOT NULL,
    openid          VARCHAR(64)     NULL,
    real_name       VARCHAR(20)     NOT NULL,
    class_name      VARCHAR(30)     NULL        COMMENT '班级名称，学生必填，教师/管理员可为空',
    status          TINYINT         NOT NULL DEFAULT 1  COMMENT '1=启用, 0=禁用',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    UNIQUE KEY uk_users_username (username),
    UNIQUE KEY uk_users_openid (openid),
    KEY idx_users_status (status),
    KEY idx_users_class (class_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 2. roles 角色表
-- ============================================================
CREATE TABLE IF NOT EXISTS roles (
    role_id         INT             NOT NULL AUTO_INCREMENT,
    role_name       VARCHAR(30)     NOT NULL,
    description     VARCHAR(100)    NULL,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (role_id),
    UNIQUE KEY uk_roles_name (role_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 3. permissions 权限表
-- ============================================================
CREATE TABLE IF NOT EXISTS permissions (
    permission_id   INT             NOT NULL AUTO_INCREMENT,
    permission_code VARCHAR(60)     NOT NULL,
    description     VARCHAR(100)    NULL,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (permission_id),
    UNIQUE KEY uk_permissions_code (permission_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 4. user_role 用户-角色映射表
-- ============================================================
CREATE TABLE IF NOT EXISTS user_role (
    user_id         VARCHAR(20)     NOT NULL,
    role_id         INT             NOT NULL,
    PRIMARY KEY (user_id, role_id),
    CONSTRAINT fk_ur_user FOREIGN KEY (user_id) REFERENCES users(user_id),
    CONSTRAINT fk_ur_role FOREIGN KEY (role_id) REFERENCES roles(role_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 5. role_permission 角色-权限映射表
-- ============================================================
CREATE TABLE IF NOT EXISTS role_permission (
    role_id         INT             NOT NULL,
    permission_id   INT             NOT NULL,
    PRIMARY KEY (role_id, permission_id),
    CONSTRAINT fk_rp_role FOREIGN KEY (role_id) REFERENCES roles(role_id),
    CONSTRAINT fk_rp_perm FOREIGN KEY (permission_id) REFERENCES permissions(permission_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 6. courses 课程表
-- ============================================================
CREATE TABLE IF NOT EXISTS courses (
    course_id       VARCHAR(20)     NOT NULL,
    course_name     VARCHAR(50)     NOT NULL,
    teacher_id      VARCHAR(20)     NOT NULL,
    term            VARCHAR(20)     NOT NULL,
    credit          DECIMAL(3,1)    NULL,
    status          TINYINT         NOT NULL DEFAULT 1  COMMENT '1=启用, 0=停用',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (course_id),
    UNIQUE KEY uk_courses_name (course_name),
    KEY idx_courses_teacher_term (teacher_id, term),
    CONSTRAINT fk_courses_teacher FOREIGN KEY (teacher_id) REFERENCES users(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 7. scores 成绩表
-- ============================================================
CREATE TABLE IF NOT EXISTS scores (
    score_id        BIGINT          NOT NULL AUTO_INCREMENT,
    student_id      VARCHAR(20)     NOT NULL,
    course_id       VARCHAR(20)     NOT NULL,
    score           DECIMAL(5,2)    NOT NULL        COMMENT '原始分数 0-100',
    exam_date       DATE            NOT NULL,
    exam_batch      VARCHAR(20)     NOT NULL        COMMENT '期中/期末/单元测验/平时',
    status          TINYINT         NOT NULL DEFAULT 1  COMMENT '1=有效, 0=标记删除',
    -- 派生字段
    total_score     DECIMAL(6,2)    NULL            COMMENT '总分缓存',
    avg_score       DECIMAL(5,2)    NULL            COMMENT '平均分缓存',
    rank_no         INT             NULL            COMMENT '排名缓存',
    level_tag       VARCHAR(10)     NULL            COMMENT '等级标签',
    comment_text    VARCHAR(200)    NULL            COMMENT '自动评语',
    stat_version    INT             NOT NULL DEFAULT 0  COMMENT '统计版本号',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (score_id),
    -- status=1 的有效记录保持唯一；status=0 的逻辑删除记录不阻止重新录入
    UNIQUE KEY uk_score_once (student_id, course_id, exam_batch, status),
    KEY idx_scores_student_course_batch (student_id, course_id, exam_batch),
    KEY idx_scores_course_batch (course_id, exam_batch),
    KEY idx_scores_rank (rank_no),
    CONSTRAINT chk_score_range CHECK (score >= 0 AND score <= 100),
    CONSTRAINT fk_scores_student FOREIGN KEY (student_id) REFERENCES users(user_id),
    CONSTRAINT fk_scores_course FOREIGN KEY (course_id) REFERENCES courses(course_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 8. sys_config 系统配置表
-- ============================================================
CREATE TABLE IF NOT EXISTS sys_config (
    config_id       BIGINT          NOT NULL AUTO_INCREMENT,
    config_key      VARCHAR(64)     NOT NULL,
    config_value    VARCHAR(255)    NOT NULL,
    config_type     VARCHAR(20)     NOT NULL        COMMENT 'int/string/json/bool',
    scope           VARCHAR(20)     NOT NULL DEFAULT 'global',
    remark          VARCHAR(255)    NULL,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (config_id),
    UNIQUE KEY uk_sys_config_key (config_key),
    KEY idx_sys_config_scope (scope)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 9. audit_log 审计日志表
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_log (
    log_id          BIGINT          NOT NULL AUTO_INCREMENT,
    trace_id        VARCHAR(40)     NOT NULL,
    operator_id     VARCHAR(20)     NOT NULL,
    action          VARCHAR(50)     NOT NULL,
    target_type     VARCHAR(30)     NOT NULL,
    target_id       VARCHAR(50)     NOT NULL,
    detail_json     TEXT            NULL,
    result_code     INT             NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (log_id),
    KEY idx_audit_trace (trace_id),
    KEY idx_audit_operator_time (operator_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 10. ai_analysis AI 分析记录表
-- ============================================================
CREATE TABLE IF NOT EXISTS ai_analysis (
    analysis_id     BIGINT          NOT NULL AUTO_INCREMENT,
    analysis_type   VARCHAR(30)     NOT NULL        COMMENT 'student_advice/class_overview/exam_paper/combined',
    target_id       VARCHAR(50)     NOT NULL        COMMENT '学生ID/班级ID/试卷ID',
    input_snapshot  TEXT            NULL            COMMENT '本次分析数据快照JSON',
    prompt_text     TEXT            NULL            COMMENT '提示词(可选保存,脱敏)',
    result_text     TEXT            NOT NULL        COMMENT 'AI返回结果',
    provider        VARCHAR(20)     NOT NULL DEFAULT 'mock'  COMMENT 'mock/free_api/custom_api',
    model_name      VARCHAR(50)     NULL,
    status          VARCHAR(10)     NOT NULL DEFAULT 'success'  COMMENT 'success/failed',
    error_message   VARCHAR(500)    NULL,
    token_used      INT             NULL,
    duration_ms     INT             NULL,
    created_by      VARCHAR(20)     NOT NULL,
    trace_id        VARCHAR(40)     NOT NULL,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (analysis_id),
    KEY idx_ai_analysis_type (analysis_type),
    KEY idx_ai_analysis_target (target_id),
    KEY idx_ai_analysis_creator (created_by, created_at),
    CONSTRAINT fk_ai_analysis_creator FOREIGN KEY (created_by) REFERENCES users(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 11. exam_paper 试卷表
-- ============================================================
CREATE TABLE IF NOT EXISTS exam_paper (
    paper_id        BIGINT          NOT NULL AUTO_INCREMENT,
    title           VARCHAR(100)    NOT NULL,
    subject         VARCHAR(50)     NOT NULL,
    exam_batch      VARCHAR(20)     NULL,
    raw_text        TEXT            NOT NULL        COMMENT '试卷原始文本',
    key_points_json TEXT            NULL            COMMENT '考点分析结果JSON',
    difficulty_level VARCHAR(10)    NULL            COMMENT '简单/中等/较难',
    question_count  INT             NULL,
    created_by      VARCHAR(20)     NOT NULL,
    trace_id        VARCHAR(40)     NOT NULL,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (paper_id),
    KEY idx_exam_paper_creator (created_by, created_at),
    CONSTRAINT fk_exam_paper_creator FOREIGN KEY (created_by) REFERENCES users(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 12. messages 师生互动留言表
-- ============================================================
CREATE TABLE IF NOT EXISTS messages (
    message_id       BIGINT          NOT NULL AUTO_INCREMENT,
    sender_id        VARCHAR(20)     NOT NULL,
    receiver_id      VARCHAR(20)     NOT NULL,
    course_id        VARCHAR(20)     NULL,
    exam_batch       VARCHAR(20)     NULL,
    related_score_id BIGINT          NULL,
    title            VARCHAR(100)    NOT NULL,
    content          TEXT            NOT NULL,
    is_read          TINYINT         NOT NULL DEFAULT 0 COMMENT '0=未读, 1=已读',
    read_at          DATETIME        NULL,
    status           TINYINT         NOT NULL DEFAULT 1 COMMENT '1=有效, 0=删除',
    created_at       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (message_id),
    KEY idx_messages_receiver_read (receiver_id, is_read, created_at),
    KEY idx_messages_sender_time (sender_id, created_at),
    KEY idx_messages_course_batch (course_id, exam_batch),
    CONSTRAINT fk_messages_sender FOREIGN KEY (sender_id) REFERENCES users(user_id),
    CONSTRAINT fk_messages_receiver FOREIGN KEY (receiver_id) REFERENCES users(user_id),
    CONSTRAINT fk_messages_course FOREIGN KEY (course_id) REFERENCES courses(course_id),
    CONSTRAINT fk_messages_score FOREIGN KEY (related_score_id) REFERENCES scores(score_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
-- 教师数据范围绑定（管理员维护，教师默认无全校范围）
CREATE TABLE IF NOT EXISTS teacher_class_bindings (
    binding_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    teacher_id VARCHAR(20) NOT NULL,
    class_name VARCHAR(30) NOT NULL,
    status SMALLINT NOT NULL DEFAULT 1,
    created_by VARCHAR(20) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_teacher_class_binding (teacher_id, class_name),
    CONSTRAINT fk_teacher_class_teacher FOREIGN KEY (teacher_id) REFERENCES users(user_id),
    CONSTRAINT fk_teacher_class_creator FOREIGN KEY (created_by) REFERENCES users(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS teacher_course_bindings (
    binding_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    teacher_id VARCHAR(20) NOT NULL,
    course_id VARCHAR(20) NOT NULL,
    status SMALLINT NOT NULL DEFAULT 1,
    created_by VARCHAR(20) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_teacher_course_binding (teacher_id, course_id),
    CONSTRAINT fk_teacher_course_teacher FOREIGN KEY (teacher_id) REFERENCES users(user_id),
    CONSTRAINT fk_teacher_course_course FOREIGN KEY (course_id) REFERENCES courses(course_id),
    CONSTRAINT fk_teacher_course_creator FOREIGN KEY (created_by) REFERENCES users(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 导入批次审计账本（预览不写入，仅 confirm 成功时生成）
CREATE TABLE IF NOT EXISTS import_batches (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    import_batch_id VARCHAR(36) NOT NULL,
    import_type VARCHAR(20) NOT NULL,
    operator_user_id VARCHAR(20) NOT NULL,
    source_filename VARCHAR(255) NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'processing',
    total_rows INT NOT NULL DEFAULT 0,
    success_rows INT NOT NULL DEFAULT 0,
    failed_rows INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME NULL,
    rolled_back_at DATETIME NULL,
    rollback_operator_user_id VARCHAR(20) NULL,
    rollback_summary TEXT NULL,
    metadata_json TEXT NULL,
    UNIQUE KEY uk_import_batches_uuid (import_batch_id),
    CONSTRAINT fk_import_batches_operator FOREIGN KEY (operator_user_id) REFERENCES users(user_id),
    CONSTRAINT fk_import_batches_rollback_operator FOREIGN KEY (rollback_operator_user_id) REFERENCES users(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS import_batch_entries (
    id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    import_batch_id VARCHAR(36) NOT NULL,
    entity_type VARCHAR(20) NOT NULL,
    entity_id VARCHAR(50) NOT NULL,
    action_type VARCHAR(20) NOT NULL,
    before_snapshot TEXT NULL,
    after_snapshot TEXT NOT NULL,
    row_number INT NULL,
    rollback_status VARCHAR(20) NULL,
    rollback_reason VARCHAR(255) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_import_batch_entry (import_batch_id, entity_type, entity_id, action_type),
    CONSTRAINT fk_import_batch_entries_batch FOREIGN KEY (import_batch_id)
        REFERENCES import_batches(import_batch_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ai_analysis_feedback (
    id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    analysis_id BIGINT NOT NULL,
    user_id VARCHAR(20) NOT NULL,
    rating VARCHAR(20) NOT NULL,
    comment VARCHAR(500) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_ai_feedback_user (analysis_id, user_id),
    CONSTRAINT fk_ai_feedback_analysis FOREIGN KEY (analysis_id) REFERENCES ai_analysis(analysis_id),
    CONSTRAINT fk_ai_feedback_user FOREIGN KEY (user_id) REFERENCES users(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
