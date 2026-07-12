USE student_grade_db;

INSERT INTO courses (course_id, course_name, teacher_id, term, credit, status, created_at, updated_at)
VALUES
('CHEM01', '化学', 'T001', '2025-2026-2', 3.0, 1, NOW(), NOW()),
('BIO01', '生物', 'T001', '2025-2026-2', 3.0, 1, NOW(), NOW()),
('POL01', '政治', 'T001', '2025-2026-2', 3.0, 1, NOW(), NOW()),
('HIS01', '历史', 'T001', '2025-2026-2', 3.0, 1, NOW(), NOW()),
('GEO01', '地理', 'T001', '2025-2026-2', 3.0, 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE
  teacher_id = VALUES(teacher_id),
  term = VALUES(term),
  credit = VALUES(credit),
  status = 1,
  updated_at = NOW();
