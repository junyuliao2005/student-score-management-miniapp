# 学生成绩管理小程序 + AI 学情诊断辅助系统

## 项目定位

以学生成绩管理为主线，以 AI 学情分析为亮点的软件工程课程设计项目。

- **核心功能：** 用户登录与角色路由、成绩录入/修改/查询、成绩发布、家长查看与签名确认、总分/平均分/排名自动计算、等级评定、自动评语、低分/偏科预警、基础数据维护、审计日志
- **亮点功能：** AI 个性化学习建议、AI 班级学情分析、AI 试卷考点分析（Mock 模式可演示）

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | 微信小程序原生开发 |
| 后端 | Python 3.9+ / Flask 2.3+ |
| 数据库 | MySQL 8.0 / InnoDB |
| 认证 | JWT (PyJWT) |
| 权限 | 简化版 RBAC (5表模型) |
| AI | 可选模块，支持 Mock 模式 |

## 项目目录

```
backend/                  后端 Flask 工程
  app.py                  启动入口
  config.py               配置类
  requirements.txt        Python 依赖
  .env.example            环境变量模板
  app/
    __init__.py           Application Factory
    extensions.py         扩展初始化
    models/               ORM 模型（11张表）
    routes/               Flask 蓝图路由
    services/             业务逻辑层
    middleware/            中间件（JWT/权限/trace/错误处理）
    utils/                工具层
    tests/                单元测试
  scripts/
    init_db.py            数据库初始化脚本
    seed_demo.py          演示数据填充脚本
    run_local.py          本地启动脚本
    verify_stats.py       统计验证脚本
  sql/
    schema.sql            完整 DDL
    seed_config.sql       初始配置数据

miniprogram/              微信小程序前端工程
  app.js / app.json / app.wxss
  env.js                  API 配置
  utils/                  工具层
  pages/                  页面
  components/             公共组件

README.md                 本文件
```

## 本地运行指南

### 1. 环境准备

- Python 3.9+
- MySQL 8.0+
- 微信开发者工具

### 2. 后端启动

```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境 (Windows)
.venv\Scripts\activate

# 激活虚拟环境 (macOS/Linux)
# source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 复制并编辑环境变量
cp .env.example .env
# 编辑 .env 文件，配置数据库连接信息（DB_USER、DB_PASSWORD、DB_NAME）

# 初始化数据库（需要先启动 MySQL）
# schema.sql 内部已包含 CREATE DATABASE，首次执行无需手动建库
# 方式 A（推荐）：使用 Python 初始化脚本
python scripts/init_db.py
python scripts/seed_demo.py

# 方式 B：手动执行 SQL
# mysql -u root -p < sql/schema.sql
# mysql -u root -p < sql/seed_config.sql

# 启动 Flask 开发服务器
python app.py
```

后端默认运行在 `http://127.0.0.1:5000`

### 3. 小程序启动

1. 打开微信开发者工具
2. 导入 `miniprogram/` 目录
3. 在登录页仅开发版可见的“开发请求模式”中选择“本地”
4. 勾选“不校验合法域名”用于本地联调；体验版/正式版会强制使用云端模式

不需要反复修改并提交 `env.js`。详细说明见 `docs/本地开发请求模式.md`；手机真机不能使用电脑的 `127.0.0.1`，需要配置电脑局域网地址。

### 4. 默认测试账号

| 角色 | 用户名 | 密码 | user_id |
|------|--------|------|---------|
| 教师 | teacher01 | 123456 | T001 |
| 学生 | student01 | 123456 | S001 |
| 管理员 | admin01 | 123456 | A001 |
| 家长 | parent01 | 123456 | PARENT01（可选脚本创建） |

## 数据库表

| 表名 | 说明 |
|------|------|
| users | 用户表 |
| roles | 角色表 |
| permissions | 权限表 |
| user_role | 用户-角色映射 |
| role_permission | 角色-权限映射 |
| courses | 课程表 |
| scores | 成绩表（含派生字段） |
| sys_config | 系统配置表 |
| audit_log | 审计日志表 |
| ai_analysis | AI 分析记录表 |
| exam_paper | 试卷表 |
| messages | 师生留言表 |
| exam_publish_settings | 考试发布设置表 |
| parent_student_bindings | 家长-学生绑定表 |
| parent_score_confirmations | 家长成绩签名确认表 |

### 成绩发布与家长确认迁移

已有数据库升级时，先手动执行迁移脚本，不要重新初始化数据库：

```bash
cd backend
mysql -u root -p student_grade_db < sql/add_exam_publish_parent_tables.sql
```

如需本地演示家长端，可选执行：

```bash
cd backend
python scripts/seed_parent_demo.py
```

该脚本会幂等创建 `parent01 / 123456`，并尽量绑定一个初中、一个高中真实学生；不会清空或覆盖已有成绩数据。

## AI 模块说明

AI 模块为可选模块，默认使用 Mock 模式：

- **Mock 模式（默认）：** 无外部 API 依赖，基于本地规则生成模拟分析结果，可直接演示
- **真实 API 模式：** 支持接入通义千问/DeepSeek/Moonshot 等 OpenAI 兼容 API

### Mock 模式工作原理

当未配置 `AI_API_KEY` 或 `AI_PROVIDER=mock` 时，系统自动使用 Mock 模式：

- **学生学习建议：** 基于学生真实成绩数据，自动分析优势科目（≥85分）、薄弱科目（<60分），生成个性化学习建议
- **班级学情分析：** 统计班级各科平均分、及格率、优秀率，识别整体薄弱环节
- **试卷考点分析：** 根据试卷文本中的关键词（如"三角函数""极限"）识别考点，结合课程数据生成分析
- **试卷图片分析：** 支持上传试卷图片，Mock 模式根据标题、学科、批次和图片信息生成视觉分析演示结果
- **个性化复习建议：** 综合学生薄弱科目和试卷考点，生成针对性复习计划

Mock 模式返回的数据结构与真实 API 兼容，但响应会明确包含 `provider`、`model`、`mode`、`is_mock`、`trace_id`、`generated_at` 和 `usage`。前端必须区分 real、mock 与 fallback，Mock 不得冒充真实模型结果。

## 真实数据导入

- 学生基础信息导入：管理员进入小程序"用户管理" → "批量导入学生"，上传 `.xlsx` 后先预览校验，再确认写入。模板说明见 `docs/学生基础信息批量导入模板说明.md`。
- 成绩导入：教师/管理员进入"成绩录入" → "批量导入成绩"，上传 `.xlsx` 后 preview + confirm。模板说明见 `docs/成绩批量导入模板说明.md`。
- 真实数据集适配、宽表转长表和课程导入后续方案见 `docs/真实数据集适配说明.md`。
- 智能 Excel 适配器：规则识别版脚本 `backend/scripts/convert_score_test_excels.py` 可扫描 `Score test/` 下原始 Excel，生成 `students_import_ready.xlsx`、`scores_import_ready.xlsx`、`courses_required.xlsx` 和转换报告。该工具不写数据库、不调用 AI，说明见 `docs/智能Excel适配器说明.md`。

## 体验版增强功能

- 普通 JSON API 已通过 `wx.cloud.callContainer` 调用微信云托管服务，体验版不依赖 request 合法域名。
- 统计分析新增总分排名：按学期、考试批次、班级实时聚合，不新增数据库表。
- 统计分析新增荣誉榜：总分前 10、单科第一、优秀学生。
- 学生端“我的成绩”新增总分、平均分、班级排名、总排名和薄弱科目提示。
- 系统配置新增成绩显示设置：是否显示总分、排名、班级统计、预警提示。
- 成绩发布闭环：教师/管理员可创建发布设置、发布/撤回成绩，学生端和家长端只展示已发布成绩。
- 家长端：支持家长绑定学生、查看孩子已发布成绩、按发布设置控制展示字段、文本签名确认。

当前 MVP 暂未实现定时发布、手写签名图片和复杂通知系统。教师任教范围已经通过班级与课程双绑定实现，未绑定教师默认无全校数据权限。

相关文档：

- `docs/朋友体验版测试清单.md`
- `docs/答辩演示路线.md`
- `docs/云端体验版部署说明.md`
- `docs/AI真实模型接入说明.md`

### 接入真实 AI API

在 `.env` 中配置以下参数即可切换到真实 API：

```env
AI_PROVIDER=openai_compatible
AI_API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
AI_API_KEY=你的API密钥
AI_MODEL=qwen-turbo
AI_MOCK_ENABLED=false
```

支持的服务商（OpenAI 兼容接口）：
| 服务商 | AI_API_BASE_URL | AI_MODEL 示例 |
|--------|----------------|---------------|
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-turbo` |
| DeepSeek 专用 Provider | `https://api.deepseek.com/chat/completions` | `deepseek-v4-pro` |
| Moonshot | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` |
| 智谱 GLM | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-flash` |

**降级机制：** 如果 `AI_MOCK_ENABLED=true`（默认值），真实 API 调用失败时会自动降级到 Mock 模式，不影响系统运行。如果 `AI_MOCK_ENABLED=false`，API 调用失败会返回错误，且配置不完整（如缺少 `AI_API_BASE_URL` 或 `AI_MODEL`）时也会直接报错，不会静默降级。

**安全说明：** 小程序前端不直接保存或传递 API Key，所有 AI 请求均通过 Flask 后端代理完成。API Key 仅存在于后端 `.env` 配置文件中。

### 视觉模型配置预留

试卷图片分析默认使用 Mock 模式，不调用外部视觉 API。如后续要接入 OpenAI 兼容视觉模型，可在 `.env` 中配置：

```env
AI_VISION_PROVIDER=openai_compatible_vision
AI_VISION_API_BASE_URL=
AI_VISION_API_KEY=
AI_VISION_MODEL=
AI_VISION_TIMEOUT=60
AI_VISION_MAX_IMAGE_MB=10
```

如果 `AI_MOCK_ENABLED=false` 且视觉模型配置缺失，接口会返回明确错误，不会暴露 API Key 给小程序。

### 输入安全

AI 模块内置文本安全处理：
- 最大输入长度限制（6000字符）
- 自动检测并拦截 Prompt 注入攻击模式
- 空白字符规范化处理

## API 接口一览

### 认证接口
| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | /api/auth/login | 公开 | 用户登录 |
| GET | /api/auth/profile | 已登录 | 获取当前用户信息 |

### 用户/课程/配置管理
| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | /api/users | user:manage | 分页查询用户 |
| POST | /api/users | user:manage | 新增用户 |
| PUT | /api/users/<user_id> | user:manage | 修改用户 |
| POST | /api/users/import/preview | admin | 学生基础信息 Excel 批量导入预览 |
| POST | /api/users/import/confirm | admin | 学生基础信息 Excel 批量导入确认 |
| GET | /api/classes | ai:class_overview | 查询启用用户关联的班级列表 |
| GET | /api/options | 已登录 | 通用输入框候选项（学生/课程/班级/学期/批次等） |
| GET | /api/courses | course:manage | 分页查询课程 |
| POST | /api/courses | course:manage | 新增课程 |
| PUT | /api/courses/<course_id> | course:manage | 修改课程 |
| GET | /api/configs | config:manage | 查询所有配置 |
| PUT | /api/configs/<config_key> | config:manage | 修改配置项 |
| GET | /api/admin/roles | role:manage | 查询角色及权限 |
| GET | /api/admin/logs | log:read | 分页查询审计日志 |

### 成绩管理
| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | /api/scores | score:create | 新增成绩 |
| POST | /api/scores/import/preview | score:create | Excel 批量导入预览 |
| POST | /api/scores/import/confirm | score:create | Excel 批量导入确认 |
| PUT | /api/scores/<id> | score:update | 修改成绩 |
| GET | /api/scores | score:read:all | 教师条件分页查询 |
| GET | /api/scores/my | score:read:self | 学生查询个人成绩 |
| DELETE | /api/scores/<id> | score:update | 逻辑删除成绩 |

### 统计分析与预警
| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | /api/stats/overview | stats:read | 班级成绩概览（人数/均分/最高/最低/优秀率/及格率） |
| GET | /api/stats/rankings | stats:read | 排名列表（竞赛排名：同分同名次，1,1,3） |
| POST | /api/stats/evaluate | stats:evaluate | 触发统计刷新（总分/均分/排名/等级/评语） |
| GET | /api/warnings | warning:read | 查询预警名单（低分/偏科） |
| POST | /api/warnings/refresh | warning:refresh | 刷新预警 |

### 师生互动留言
| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | /api/messages | 已登录 | 查询当前用户可见留言，管理员可查全部 |
| POST | /api/messages | 已登录 | 创建师生留言，发送人以后端登录用户为准 |
| GET | /api/messages/unread-count | 已登录 | 查询当前用户未读留言数 |
| PUT | /api/messages/<id>/read | 已登录 | 标记单条留言已读 |
| PUT | /api/messages/read-all | 已登录 | 标记当前用户收到的留言全部已读 |
| GET | /api/messages/contacts | 已登录 | 查询留言接收人候选列表 |

### AI 分析
| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | /api/ai/student-advice | ai:student_advice | 学生个人学习建议 |
| POST | /api/ai/class-overview | ai:class_overview | 班级学情分析 |
| POST | /api/ai/exam-paper/analyze | ai:exam_analyze | 试卷考点分析 |
| POST | /api/ai/exam-paper/analyze-image | ai:exam_analyze | 试卷图片视觉考点分析（Mock MVP） |
| POST | /api/ai/combined-advice | ai:combined_advice | 个性化复习建议 |
| GET | /api/ai/history | ai:history:read | 查询 AI 分析历史 |

### 健康检查
| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | /api/health | 公开 | 服务健康检查 |

## 第3阶段接口测试示例

```bash
# 1. 管理员登录获取 Token
curl -X POST http://127.0.0.1:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin01","password":"123456"}'

# 2. 教师登录获取 Token
curl -X POST http://127.0.0.1:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"teacher01","password":"123456"}'

# 3. 先创建课程（用管理员 Token）
curl -X POST http://127.0.0.1:5000/api/courses \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <admin_token>" \
  -d '{"course_id":"MATH01","course_name":"高等数学","teacher_id":"T001","term":"2025-2026-2"}'

# 4. 教师录入成绩
curl -X POST http://127.0.0.1:5000/api/scores \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <teacher_token>" \
  -d '{"student_id":"S001","course_id":"MATH01","score":88.5,"exam_date":"2026-03-20","exam_batch":"期中"}'

# 5. 教师查询成绩
curl "http://127.0.0.1:5000/api/scores?course_id=MATH01&page=1&page_size=20" \
  -H "Authorization: Bearer <teacher_token>"

# 6. 学生登录
curl -X POST http://127.0.0.1:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"student01","password":"123456"}'

# 7. 学生查询自己的成绩
curl "http://127.0.0.1:5000/api/scores/my" \
  -H "Authorization: Bearer <student_token>"
```

## 第4阶段接口测试示例

```bash
# 1. 管理员登录获取 Token
curl -X POST http://127.0.0.1:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin01","password":"123456"}'

# 2. 填充演示数据（含20个学生、5门课程、100条成绩）
cd backend && python scripts/seed_demo.py

# 3. 查询班级成绩概览
curl "http://127.0.0.1:5000/api/stats/overview?term=2025-2026-2&class_name=2025级1班" \
  -H "Authorization: Bearer <admin_token>"

# 4. 查询排名列表
curl "http://127.0.0.1:5000/api/stats/rankings?term=2025-2026-2&class_name=2025级1班&page=1&page_size=20" \
  -H "Authorization: Bearer <admin_token>"

# 5. 触发统计刷新
curl -X POST http://127.0.0.1:5000/api/stats/evaluate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <admin_token>" \
  -d '{"term":"2025-2026-2","class_name":"2025级1班"}'

# 6. 查询预警名单
curl "http://127.0.0.1:5000/api/warnings?term=2025-2026-2&class_name=2025级1班" \
  -H "Authorization: Bearer <admin_token>"

# 7. 学生查询自己的成绩（含排名、等级、评语）
curl -X POST http://127.0.0.1:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"student03","password":"123456"}'
# 用 student03 的 token 查询
curl "http://127.0.0.1:5000/api/scores/my?term=2025-2026-2" \
  -H "Authorization: Bearer <student03_token>"

# 8. 运行纯函数验证脚本（不连接数据库）
cd backend && python scripts/verify_stats.py
```

## 微信小程序前端

### 目录结构

```
miniprogram/
  app.js                    全局入口，维护登录态
  app.json                  页面路由、tabBar 配置
  app.wxss                  全局基础样式
  env.js                    后端地址配置
  sitemap.json              小程序 sitemap
  project.config.json       项目配置
  utils/
    request.js              local wx.request / cloud callContainer 统一封装
    auth.js                 登录态管理（token/roles/permissions）
    permission.js           权限检查工具
    validators.js           表单校验（分数/日期/分页）
    constants.js            常量（角色/等级/错误码）
    format.js               格式化工具（分数/日期/百分比）
  pages/
    login/                  登录页
    home/                   首页（功能入口）
    score-edit/             成绩录入/修改
    score-list/             成绩查询（教师/管理员）
    score-my/               我的成绩（学生）
    stats/                  统计分析
    warnings/               预警名单
    messages/               师生互动留言
    admin/
      users                 用户管理
      import-users/         学生基础信息批量导入
      courses               课程管理
      configs               配置管理
      logs                  日志查询
  components/
    empty-state/            空状态组件
    loading-overlay/        加载遮罩组件
    grade-table/            成绩表格组件
    score-form/             成绩表单组件
    stat-panel/             统计面板组件
    warning-card/           预警卡片组件
```

### 小程序页面说明

| 页面 | 路径 | 角色 | 说明 |
|------|------|------|------|
| 登录 | pages/login/index | 公开 | 用户名密码登录，保存 JWT，角色路由跳转 |
| 首页 | pages/home/index | 全部 | 用户信息、功能入口卡片、按权限展示菜单、退出登录 |
| 成绩录入 | pages/score-edit/index | 教师/管理员 | 录入/修改成绩，分数 0-100 校验 |
| 成绩查询 | pages/score-list/index | 教师/管理员 | 多条件筛选、分页、编辑/删除 |
| 我的成绩 | pages/score-my/index | 学生 | 个人成绩列表，含总分/均分/排名/等级/评语 |
| 统计分析 | pages/stats/index | 教师/管理员 | 概览统计 + 排名列表，支持刷新统计 |
| 预警名单 | pages/warnings/index | 教师/管理员 | 低分/偏科预警，支持刷新预警 |
| 师生留言 | pages/messages/index | 全部 | 师生互动留言、未读状态、留言回复 |
| 用户管理 | pages/admin/users | 管理员 | 新增/编辑用户 |
| 批量导入学生 | pages/admin/import-users/index | 管理员 | Excel 导入学生基础信息，preview + confirm |
| 课程管理 | pages/admin/courses | 管理员 | 新增/编辑课程 |
| 配置管理 | pages/admin/configs | 管理员 | 查看/修改系统配置 |
| 日志查询 | pages/admin/logs | 管理员 | 查看审计日志 |
| AI 学习建议 | pages/ai-advice/index | 学生/教师 | 个人学习建议，基于成绩分析 |
| AI 班级分析 | pages/ai-class/index | 教师/管理员 | 班级学情综合分析 |
| 试卷考点分析 | pages/exam-analyze/index | 教师/管理员 | 试卷考点分析 + 个性化复习建议 |

### 如何用微信开发者工具导入小程序

1. 打开**微信开发者工具**
2. 点击**导入项目**（或"添加项目"）
3. **项目目录**选择：`<PROJECT_ROOT>\miniprogram`
4. **AppID**：选择**测试号**，或点击"无 AppID"（不影响本地调试）
5. 点击**确定**导入

### 如何切换请求模式

`env.js` 默认保持 cloud。微信开发者工具的 develop 版本会在登录页显示“开发请求模式”，点击“本地”后普通 API 使用 `wx.request + BASE_URL`，文件使用 `wx.uploadFile`；点击“云端”后使用 `callContainer + 云存储临时文件`。trial/release 版本强制 cloud，详见 `docs/本地开发请求模式.md`。

### 如何联调 Flask 后端

1. **启动后端**：
   ```bash
   cd backend
   python app.py
   ```
   后端默认运行在 `http://127.0.0.1:5000`

2. **打开微信开发者工具**，导入 `miniprogram/` 目录

3. **本地调试设置**（重要）：
   - 点击右上角**详情** → **本地设置**
   - 勾选：**不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书**

4. **编译运行**：点击**编译**按钮，小程序会自动加载并连接后端

5. **登录测试**：使用默认测试账号登录

### 小程序常见问题

**请求失败怎么办？**
- 检查后端是否启动（`python app.py`）
- 检查 `env.js` 中 `BASE_URL` 是否正确
- 检查微信开发者工具是否勾选"不校验合法域名"

**127.0.0.1 连不上怎么办？**
- 确认 Flask 后端正在运行
- 尝试在浏览器访问 `http://127.0.0.1:5000/api/health` 确认后端正常
- 如果使用真机调试，需要将 `BASE_URL` 改为电脑的局域网 IP（如 `http://192.168.1.100:5000`）

**没有 AppID 怎么办？**
- 在微信开发者工具中选择"体验号"或"测试号"即可
- 本地调试不需要正式 AppID

**登录后页面空白？**
- 先访问 `/api/health` 并查看后端错误日志。
- 已有数据库只运行缺失表对应的幂等迁移，严禁为了修复缺表执行 `init_db.py` 或重导数据。
- `init_db.py` / `seed_demo.py` 只适用于明确的新建空开发库。

## 当前开发进度

- [x] 第1阶段：后端基础工程 + 数据库结构 + 基础配置
- [x] 第2阶段：用户登录、JWT、角色权限、用户/课程维护
- [x] 第3阶段：成绩录入、修改、查询
- [x] 第4阶段：统计分析、排名、等级、评语、预警
- [x] 第5阶段：微信小程序核心页面
- [x] 第6阶段：AI 智能分析模块后端
- [x] 第7阶段：AI 智能分析前端页面
- [x] 第8阶段：测试、README、演示数据、答辩说明

## 2026-07 工程化版本说明

当前版本在原有成绩管理、统计、预警、AI mock、Excel 导入和师生留言基础上增加：

- 学生/家长严格只看 `published` 成绩，撤回后立即不可见。
- 教师班级 + 课程双重授权，无绑定默认拒绝全校数据。
- DeepSeek Chat Completions Provider、Mock/Fallback 明示、OCR 预览人工修正。
- local/cloud 统一请求与上传、CloudBase 临时 URL 安全消费。
- 原子导入批次账本和快照保护的安全撤销。
- 成绩趋势、分数段、进步榜、偏科分析、家长待确认、XLSX/PDF 报告。
- AI 历史和反馈、非 root Docker、Compose 与 Kubernetes 示例。

### 已有数据库增量迁移

先备份数据库，再在 `backend` 目录人工执行；这些脚本只创建指定新表，不清空旧数据：

```powershell
python scripts/add_teacher_bindings_tables.py
python scripts/add_import_batch_tables.py
python scripts/add_ai_feedback_table.py
```

迁移后用管理员账号进入“教师范围”配置班级和课程。未配置教师会被后端默认拒绝，这是预期安全行为。

### 离线验证

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe scripts\run_all_tests.py
```

当前候选基线：Python AST 113/113、Mini Program JavaScript 43/43、JSON 38/38、pytest 31/31、组合运行时回归 19/19、统计纯函数 31/31。SQLite 离线总入口显式禁用真实 AI；此外已在本地 MySQL 备份后执行 5 张表的幂等迁移，并完成真实 Flask/MySQL 只读 HTTP 验收。独立 Python 3.12 可真实生成并解析 PDF，但项目 `.venv` 因当前包索引受限仍未安装 Pillow/ReportLab/coverage/pytest-cov。

### 真实本地集成状态

- 本地 MySQL 8 只读连接：PASS；备份与迁移报告见 `docs/本地数据库迁移报告.md`。
- Flask/MySQL HTTP：健康、四角色 JWT profile、学生/家长边界、管理列表与统计 PASS；真实密码登录留给用户凭据人工验证。
- DeepSeek：Key 元数据非空且未输出；单次有界真实连接因当前网络限制 FAIL，离线错误分类/fallback 7/7 PASS。
- OCR：真实图片解码 PASS，Mock 流程 PASS，RapidOCR 真实识别因依赖不可安装而 SKIPPED。
- coverage：pytest-cov 未安装，正式报告 SKIPPED；标准库 trace 仅提供 49.04% 参考值，不冒充 coverage.py。

### 部署入口

- 微信云托管：上传 `backend/`，容器端口 `5000`，配置生产密钥和数据库环境变量。
- Docker 开发：参考 `backend/.env.docker.example` 与 `backend/docker-compose.yml`。
- Kubernetes：参考 `backend/deploy/k8s/`，真实 Secret 不得提交 Git。
- 小程序请求模式：develop 登录页一键切换 local/cloud；trial/release 强制 cloud。

详细说明见 `docs/部署与运行说明.md`、`docs/API接口清单.md`、`docs/自动化测试报告.md` 和 `docs/作品集项目介绍.md`。
