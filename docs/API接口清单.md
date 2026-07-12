# API 接口清单

## 基础信息

- Base URL: `http://127.0.0.1:5000`
- 认证方式: JWT Bearer Token
- 响应格式: `{code, message, data, trace_id}`
- 成功响应: `code = 0`

---

## 1. 认证模块 (auth)

### POST /api/auth/login
用户登录，获取 JWT Token。

**请求体:**
```json
{"username": "teacher01", "password": "123456"}
```

**响应:**
```json
{
  "code": 0,
  "data": {
    "token": "eyJ...",
    "user": {"user_id": "T001", "real_name": "张老师", "class_name": null},
    "roles": ["teacher"],
    "permissions": ["score:create", "score:update", ...]
  }
}
```

### GET /api/auth/profile
获取当前用户信息（需登录）。

---

## 2. 用户管理 (users)

### GET /api/users?page=1&page_size=20
分页查询用户列表。权限: `user:manage`

### POST /api/users
新增用户。权限: `user:manage`

**请求体:**
```json
{"user_id": "S011", "username": "student11", "password": "123456", "real_name": "新同学", "class_name": "2025级1班", "role": "student"}
```

### PUT /api/users/<user_id>
修改用户。权限: `user:manage`

### POST /api/users/import/preview
学生基础信息 Excel 批量导入预览。权限: 管理员。

**请求格式:** `multipart/form-data`

**字段:**
- `file`: `.xlsx` 文件

**模板字段:**
- 必填: 学号/student_id、姓名/real_name/student_name、班级/class_name
- 可选: 用户名/username、年级/grade、学校/school_name、性别/gender、手机号/phone、初始密码/password

**响应:**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "import_id": "b7f0...",
    "total_rows": 30,
    "valid_rows": 28,
    "duplicate_rows": 1,
    "error_rows": 1,
    "rows": [
      {
        "row_no": 2,
        "student_id": "S101",
        "username": "S101",
        "real_name": "张三",
        "class_name": "2025级1班",
        "role": "student",
        "status": "valid",
        "errors": []
      }
    ]
  },
  "trace_id": "..."
}
```

### POST /api/users/import/confirm
确认导入 preview 中合法且不重复的学生账号。权限: 管理员。

**请求体:**
```json
{"import_id": "b7f0..."}
```

**响应:**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "import_id": "b7f0...",
    "inserted_count": 28,
    "skipped_count": 1,
    "error_count": 1,
    "task_status": "done"
  },
  "trace_id": "..."
}
```

### GET /api/classes
查询启用用户关联的班级列表，用于 AI 班级分析选择器。权限: `ai:class_overview`

**响应:**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "classes": ["2025级1班", "2025级2班"]
  },
  "trace_id": "..."
}
```

### GET /api/options?type=students
通用输入框候选项。权限: 已登录。

支持 `type`: students, student_names, courses, course_ids, classes, terms, exam_batches, subjects, paper_titles, teachers。

学生只返回自己相关课程、学期、考试批次等；教师返回启用学生和课程等基础选项；管理员返回全部可用选项。

**响应:**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "options": [
      {"label": "2025级1班", "value": "2025级1班"}
    ]
  },
  "trace_id": "..."
}
```

---

## 3. 课程管理 (courses)

### GET /api/courses?page=1&page_size=20
分页查询课程列表。权限: `course:manage`

### POST /api/courses
新增课程。权限: `course:manage`

**请求体:**
```json
{"course_id": "MATH02", "course_name": "线性代数", "teacher_id": "T001", "term": "2025-2026-2", "credit": 3.0}
```

### PUT /api/courses/<course_id>
修改课程。权限: `course:manage`

---

## 4. 成绩管理 (scores)

### POST /api/scores
新增成绩。权限: `score:create`

**请求体:**
```json
{"student_id": "S001", "course_id": "MATH01", "score": 88.5, "exam_date": "2026-03-20", "exam_batch": "期中"}
```

**响应:**
```json
{
  "code": 0,
  "data": {
    "score_id": 1,
    "student_id": "S001",
    "course_id": "MATH01",
    "score": 88.5,
    "task_status": "done"
  }
}
```

### PUT /api/scores/<score_id>
修改成绩。权限: `score:update`

### POST /api/scores/import/preview
Excel 批量导入预览。权限: `score:create`

**请求格式:** `multipart/form-data`

**字段:**
- `file`: `.xlsx` 文件

**响应:**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "import_id": "b7f0...",
    "total_rows": 100,
    "valid_rows": 92,
    "error_rows": 5,
    "duplicate_rows": 3,
    "rows": [
      {
        "row_no": 2,
        "student_id": "S001",
        "student_name": "赵一",
        "course_id": "MATH01",
        "score": 88,
        "exam_date": "2026-04-10",
        "exam_batch": "期中",
        "status": "valid",
        "errors": []
      }
    ]
  },
  "trace_id": "..."
}
```

### POST /api/scores/import/confirm
确认导入 preview 中合法且不重复的成绩。权限: `score:create`

**请求体:**
```json
{"import_id": "b7f0..."}
```

**响应:**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "import_id": "b7f0...",
    "inserted_count": 92,
    "skipped_count": 3,
    "error_count": 5,
    "task_status": "done"
  },
  "trace_id": "..."
}
```

### GET /api/scores?page=1&page_size=20&student_id=S001&course_id=MATH01
教师分页查询成绩。权限: `score:read:all`

支持筛选: student_id, student_name, course_id, course_name, class_name, term, exam_batch

### GET /api/scores/my?term=2025-2026-2
学生查询自己的成绩。权限: `score:read:self`

### DELETE /api/scores/<score_id>
逻辑删除成绩。权限: `score:update`

---

## 5. 统计分析 (stats)

### GET /api/stats/overview?term=2025-2026-2&class_name=2025级1班
班级成绩概览。权限: `stats:read`

**响应:**
```json
{
  "code": 0,
  "data": {
    "student_count": 10,
    "score_count": 30,
    "avg_score": 76.8,
    "max_score": 100,
    "min_score": 38,
    "excellent_rate": 0.3,
    "pass_rate": 0.8,
    "low_score_count": 1
  }
}
```

### GET /api/stats/rankings?term=2025-2026-2&class_name=2025级1班&page=1&page_size=20
排名列表。权限: `stats:read`

### POST /api/stats/evaluate
触发统计刷新。权限: `stats:evaluate`

**请求体:**
```json
{"term": "2025-2026-2", "class_name": "2025级1班"}
```

---

## 6. 预警 (warnings)

### GET /api/warnings?term=2025-2026-2&class_name=2025级1班&warning_type=low_score
查询预警名单。权限: `warning:read`

### POST /api/warnings/refresh
刷新预警。权限: `warning:refresh`

---

## 7. 师生互动留言 (messages)

### GET /api/messages?page=1&page_size=20&box=received
查询当前用户可见留言。学生/教师只能查看自己发送或接收的留言，管理员可查看全部。

支持参数: page, page_size, box(received/sent), unread_only, student_id, teacher_id, course_id, exam_batch

### POST /api/messages
创建留言。发送人以后端当前登录用户为准，不信任前端传入 sender_id。

**请求体:**
```json
{
  "receiver_id": "S001",
  "title": "期中成绩反馈",
  "content": "请重点复习错题。",
  "course_id": "MATH01",
  "exam_batch": "期中"
}
```

### GET /api/messages/unread-count
查询当前用户未读留言数量。

### PUT /api/messages/<message_id>/read
标记单条留言为已读。普通用户只能标记发给自己的留言，管理员可标记任意留言。

### PUT /api/messages/read-all
标记当前用户收到的全部留言为已读。

### GET /api/messages/contacts
查询留言接收人候选列表。学生返回教师/管理员候选，教师/管理员返回学生候选。

---

## 8. AI 分析 (ai)

### POST /api/ai/student-advice
学生学习建议。权限: `ai:student_advice:self` 或 `ai:student_advice:all`

**请求体:**
```json
{"student_id": "S001", "term": "2025-2026-2"}
```

**响应:**
```json
{
  "code": 0,
  "data": {
    "strengths": "高等数学（95分，优秀）、Python程序设计（98分，优秀）",
    "weaknesses": "大学英语（92分）有提升空间",
    "advice": ["保持当前学习节奏，适当挑战更高难度的题目。"],
    "focus": "各科均衡发展，适当拓展高难度内容。",
    "encouragement": "赵一同学，你的成绩非常优秀！...",
    "analysis_id": 1,
    "provider": "mock",
    "is_mock": true
  }
}
```

### POST /api/ai/class-overview
班级学情分析。权限: `ai:class_overview`

**请求体:**
```json
{"term": "2025-2026-2", "class_name": "2025级1班"}
```

### POST /api/ai/exam-paper/analyze
试卷考点分析。权限: `ai:exam_analyze`

**请求体:**
```json
{"title": "期中考试试卷", "subject": "数学", "exam_batch": "期中", "paper_text": "试卷文本内容..."}
```

### POST /api/ai/exam-paper/analyze-image
试卷图片视觉考点分析。权限: `ai:exam_analyze`

**请求格式:** `multipart/form-data`

**字段:**
- `title`: 试卷标题，必填
- `subject`: 学科，必填
- `exam_batch`: 考试批次，必填
- `image`: 图片文件，必填，支持 jpg/jpeg/png/webp，默认最大 10MB

**响应:**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "recognized_summary": "本试卷主要包含选择题、填空题和综合应用题。",
    "key_points": ["函数性质", "方程求解", "应用题建模"],
    "knowledge_distribution": [
      {"name": "基础概念", "percent": 30},
      {"name": "计算能力", "percent": 35},
      {"name": "综合应用", "percent": 35}
    ],
    "difficulty": "中等",
    "difficulty_reason": "基础题和综合题比例较均衡。",
    "error_prone_points": ["审题遗漏条件", "计算符号错误"],
    "review_suggestions": ["复习核心公式与基础概念"],
    "provider": "mock",
    "is_mock": true
  },
  "trace_id": "..."
}
```

### POST /api/ai/combined-advice
个性化复习建议。权限: `ai:combined_advice`

**请求体:**
```json
{"student_id": "S001", "paper_id": 1, "term": "2025-2026-2"}
```

### GET /api/ai/history?page=1&page_size=20&analysis_type=student_advice
查询 AI 分析历史。权限: `ai:history:read`

---

## 9. 管理 (admin)

### GET /api/admin/roles
查询角色及权限列表。权限: `role:manage`

### GET /api/admin/logs?page=1&page_size=20
分页查询审计日志。权限: `log:read`

---

## 10. 配置 (config)

### GET /api/configs
查询所有系统配置。权限: `config:manage`

### PUT /api/configs/<config_key>
修改配置项。权限: `config:manage`

**请求体:**
```json
{"config_value": "70"}
```

---

## 11. 导入批次账本（admin）

### GET /api/import-batches

管理员分页查询批次。筛选：`page`、`page_size`、`import_type`、`status`、`operator_user_id`。列表不返回快照。

### GET /api/import-batches/<import_batch_id>

管理员查看批次与安全快照。快照仅含成绩/用户撤销必需字段，不含密码、密码哈希、Token、Key、openid。

### POST /api/import-batches/<import_batch_id>/rollback

管理员执行安全撤销。仅 `completed` 批次可撤销；返回 `success_count`、`skipped_count`、`failed_count` 和逐条原因。已撤销批次不能重复撤销。

成绩和学生导入 confirm 响应新增向后兼容字段：`import_batch_id`。

## 12. 健康检查

### GET /api/health
服务健康检查。无需认证。

**响应:**
```json
{"code": 0, "data": {"status": "ok", "version": "1.0.0"}, "message": "success"}
```

---

## 错误码

| 错误码 | HTTP 状态 | 说明 |
|--------|-----------|------|
| 0 | 200 | 成功 |
| 20001 | 400 | 分数超出范围 |
| 20002 | 400 | 成绩记录重复 |
| 20003 | 400 | 课程不存在 |
| 20004 | 400 | 学生不存在 |
| 20005 | 400 | 配置缺失 |
| 20006 | 400 | 成绩导入文件或预览数据无效 |
| 20007 | 400 | 学生基础信息导入文件或预览数据无效 |
| 20010 | 400 | 请求参数不完整或不合法 |
| 30001 | 403 | 权限不足 |
| 40001 | 401 | Token 已过期 |
| 40002 | 401 | Token 无效 |
| 40003 | 401 | 请先登录 |
| 50001 | 500 | 数据库操作失败 |
| 50002 | 500 | 统计刷新失败 |
| 50003 | 500 | 服务器内部错误 |
| 60001 | 500 | AI 分析失败 |
| 60002 | 500 | AI 输入过长 |
| 60003 | 500 | AI 请求频率限制 |

## 13. 按需统计与报告

- `GET /api/stats/trends`：教师/管理员班级或学生趋势，需指定 `class_name` 或 `student_id`。
- `GET /api/stats/my-trend`：当前学生已发布成绩趋势。
- `GET /api/stats/distribution`：分数段，必须指定 `exam_batch`。
- `GET /api/stats/progress-rankings`：进步榜，必须指定 `term`、`baseline_batch`、`current_batch`，分页。
- `GET /api/stats/bias-analysis`：偏科分析，必须指定 `term`、`exam_batch`，分页。
- `GET /api/reports/scores/export`：教师/管理员范围内成绩 XLSX，必须指定 `exam_batch`，最多 10000 条。
- `GET /api/reports/students/<student_id>/scores.pdf`：学生/家长只生成已发布可见成绩；教师受绑定范围限制。
- `GET /api/exam-publish/<id>/confirmations/export`：家长确认表 XLSX。

文件接口返回 `{filename, mime_type, content_base64, row_count}`，便于 local/cloud 两种小程序请求模式统一处理。

## 14. AI 历史反馈

- `GET /api/ai/history`：学生看本人、教师看本人创建、管理员看全部。
- `POST /api/ai/history/<analysis_id>/feedback`：请求 `{rating: useful|neutral|not_useful, comment?}`；只能评价当前用户可见分析。

## 本地集成验证

Flask URL map 当前共 80 个方法+路径，发布候选关键路由 16/16 注册。2026-07-11 本地 Flask/MySQL HTTP 验证覆盖 health、四角色 profile、学生本人 published 成绩、家长孩子、教师范围、考试发布、导入批次、AI 历史、options 和统计概览；密码登录因不读取凭据而保留人工验证。该说明不新增或改变接口契约。
