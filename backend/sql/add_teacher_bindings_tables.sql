-- Non-destructive teacher data-scope migration. Safe to run repeatedly.
CREATE TABLE IF NOT EXISTS teacher_class_bindings (
    binding_id INT NOT NULL AUTO_INCREMENT,
    teacher_id VARCHAR(20) NOT NULL,
    class_name VARCHAR(30) NOT NULL,
    status SMALLINT NOT NULL DEFAULT 1,
    created_by VARCHAR(20) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (binding_id),
    UNIQUE KEY uk_teacher_class_binding (teacher_id, class_name),
    KEY idx_teacher_class_teacher (teacher_id),
    KEY idx_teacher_class_name (class_name),
    CONSTRAINT fk_teacher_class_teacher FOREIGN KEY (teacher_id) REFERENCES users (user_id),
    CONSTRAINT fk_teacher_class_creator FOREIGN KEY (created_by) REFERENCES users (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS teacher_course_bindings (
    binding_id INT NOT NULL AUTO_INCREMENT,
    teacher_id VARCHAR(20) NOT NULL,
    course_id VARCHAR(20) NOT NULL,
    status SMALLINT NOT NULL DEFAULT 1,
    created_by VARCHAR(20) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (binding_id),
    UNIQUE KEY uk_teacher_course_binding (teacher_id, course_id),
    KEY idx_teacher_course_teacher (teacher_id),
    KEY idx_teacher_course_course (course_id),
    CONSTRAINT fk_teacher_course_teacher FOREIGN KEY (teacher_id) REFERENCES users (user_id),
    CONSTRAINT fk_teacher_course_course FOREIGN KEY (course_id) REFERENCES courses (course_id),
    CONSTRAINT fk_teacher_course_creator FOREIGN KEY (created_by) REFERENCES users (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
