-- Non-destructive AI feedback migration. Safe to run repeatedly.
CREATE TABLE IF NOT EXISTS ai_analysis_feedback (
    id BIGINT NOT NULL AUTO_INCREMENT,
    analysis_id BIGINT NOT NULL,
    user_id VARCHAR(20) NOT NULL,
    rating VARCHAR(20) NOT NULL,
    comment VARCHAR(500) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_ai_feedback_user (analysis_id, user_id),
    KEY idx_ai_feedback_analysis (analysis_id),
    KEY idx_ai_feedback_user (user_id),
    CONSTRAINT fk_ai_feedback_analysis FOREIGN KEY (analysis_id) REFERENCES ai_analysis(analysis_id),
    CONSTRAINT fk_ai_feedback_user FOREIGN KEY (user_id) REFERENCES users(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
