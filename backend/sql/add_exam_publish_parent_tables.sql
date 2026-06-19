-- 成绩发布与家长签名确认 MVP 迁移脚本
-- 只新增表和 parent 角色；不清空、不重建、不导入成绩数据。

CREATE TABLE IF NOT EXISTS exam_publish_settings (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  exam_name VARCHAR(100) NOT NULL,
  term VARCHAR(50) NOT NULL,
  exam_batch VARCHAR(100) NOT NULL,
  grade_name VARCHAR(50) NULL,
  class_name VARCHAR(100) NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'draft',
  show_total TINYINT(1) NOT NULL DEFAULT 1,
  show_rank TINYINT(1) NOT NULL DEFAULT 1,
  show_grade_rank TINYINT(1) NOT NULL DEFAULT 1,
  show_class_average TINYINT(1) NOT NULL DEFAULT 1,
  show_subject_scores TINYINT(1) NOT NULL DEFAULT 1,
  require_parent_signature TINYINT(1) NOT NULL DEFAULT 0,
  publish_time DATETIME NULL,
  withdraw_time DATETIME NULL,
  created_by VARCHAR(50) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_exam_publish_lookup (term, exam_batch, status),
  INDEX idx_exam_publish_scope (grade_name, class_name, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS parent_student_bindings (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  parent_user_id VARCHAR(50) NOT NULL,
  student_user_id VARCHAR(50) NOT NULL,
  relation VARCHAR(50) DEFAULT '家长',
  status TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_parent_student (parent_user_id, student_user_id),
  INDEX idx_parent_binding_parent (parent_user_id, status),
  INDEX idx_parent_binding_student (student_user_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS parent_score_confirmations (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  publish_id BIGINT NOT NULL,
  parent_user_id VARCHAR(50) NOT NULL,
  student_user_id VARCHAR(50) NOT NULL,
  confirm_status VARCHAR(20) NOT NULL DEFAULT 'pending',
  signature_text VARCHAR(100) NULL,
  confirmed_at DATETIME NULL,
  remark VARCHAR(255) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_parent_confirmation (publish_id, parent_user_id, student_user_id),
  INDEX idx_parent_confirmation_publish (publish_id, confirm_status),
  INDEX idx_parent_confirmation_parent (parent_user_id, student_user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO roles (role_name, description, created_at)
SELECT 'parent', '家长', NOW()
WHERE NOT EXISTS (SELECT 1 FROM roles WHERE role_name = 'parent');
