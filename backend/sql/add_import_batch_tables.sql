-- Non-destructive import ledger migration. Safe to run repeatedly.
CREATE TABLE IF NOT EXISTS import_batches (
    id INT NOT NULL AUTO_INCREMENT,
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
    PRIMARY KEY (id),
    UNIQUE KEY uk_import_batches_uuid (import_batch_id),
    KEY idx_import_batches_type (import_type),
    KEY idx_import_batches_status (status),
    KEY idx_import_batches_operator (operator_user_id),
    CONSTRAINT fk_import_batches_operator FOREIGN KEY (operator_user_id) REFERENCES users(user_id),
    CONSTRAINT fk_import_batches_rollback_operator FOREIGN KEY (rollback_operator_user_id) REFERENCES users(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS import_batch_entries (
    id BIGINT NOT NULL AUTO_INCREMENT,
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
    PRIMARY KEY (id),
    UNIQUE KEY uk_import_batch_entry (import_batch_id, entity_type, entity_id, action_type),
    KEY idx_import_batch_entries_batch (import_batch_id),
    CONSTRAINT fk_import_batch_entries_batch FOREIGN KEY (import_batch_id)
        REFERENCES import_batches(import_batch_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
