# 开发日志

## 第1阶段：后端基础工程 + 数据库结构 + 配置

**状态**: ✅ 已完成

**创建文件:**
- `backend/app.py` — Flask 启动入口
- `backend/config.py` — 配置类（DB/JWT/AI）
- `backend/requirements.txt` — Python 依赖
- `backend/.env.example` — 环境变量模板
- `backend/app/__init__.py` — Application Factory
- `backend/app/extensions.py` — SQLAlchemy/CORS 初始化
- `backend/app/models/` — 11 张表的 ORM 模型
- `backend/app/utils/errors.py` — BusinessError + ErrorCode
- `backend/app/utils/response.py` — 统一响应
- `backend/app/utils/validators.py` — 校验工具
- `backend/app/utils/hash_util.py` — 密码哈希
- `backend/app/utils/time_util.py` — 时间工具
- `backend/app/middleware/` — trace/错误处理中间件
- `backend/sql/schema.sql` — 完整 DDL
- `backend/sql/seed_config.sql` — 初始配置数据

**实现功能:**
- Flask Application Factory 模式
- 11 张表 ORM 模型定义
- 统一错误码和响应格式
- 中间件注册

---

## 第2阶段：登录/JWT/RBAC/用户课程管理

**状态**: ✅ 已完成

**创建文件:**
- `backend/app/middleware/jwt_middleware.py` — JWT 认证中间件
- `backend/app/middleware/permission_middleware.py` — 权限校验中间件
- `backend/app/services/auth_manager.py` — 登录服务
- `backend/app/services/audit_service.py` — 审计日志
- `backend/app/services/config_loader.py` — 配置读取
- `backend/app/services/user_service.py` — 用户管理
- `backend/app/services/course_service.py` — 课程管理
- `backend/app/routes/auth_routes.py` — 认证路由
- `backend/app/routes/config_routes.py` — 配置路由
- `backend/app/routes/admin_routes.py` — 管理路由
- `backend/scripts/init_db.py` — 数据库初始化脚本

**实现功能:**
- POST /api/auth/login — JWT 登录
- GET /api/auth/profile — 获取用户信息
- RBAC 权限校验（19 个权限点）
- 用户 CRUD、课程 CRUD、配置管理
- 审计日志记录

---

## 第3阶段：成绩录入/修改/查询

**状态**: ✅ 已完成

**创建文件:**
- `backend/app/services/score_service.py` — 成绩管理服务
- `backend/app/routes/score_routes.py` — 成绩路由
- `backend/app/utils/ranking.py` — 排名算法

**实现功能:**
- POST /api/scores — 新增成绩
- PUT /api/scores/:id — 修改成绩
- GET /api/scores — 教师分页查询
- GET /api/scores/my — 学生查询自己
- DELETE /api/scores/:id — 逻辑删除
- 唯一性约束、分数范围校验

---

## 第4阶段：统计分析/排名/等级/评语/预警

**状态**: ✅ 已完成

**创建文件:**
- `backend/app/services/stats_service.py` — 统计服务
- `backend/app/services/comment_service.py` — 评语生成
- `backend/app/services/warning_calculator.py` — 预警计算
- `backend/app/routes/stats_routes.py` — 统计路由
- `backend/app/routes/warning_routes.py` — 预警路由
- `backend/scripts/seed_demo.py` — 演示数据填充
- `backend/scripts/verify_stats.py` — 纯函数验证

**实现功能:**
- GET /api/stats/overview — 班级概览
- GET /api/stats/rankings — 排名列表
- POST /api/stats/evaluate — 触发统计刷新
- GET /api/warnings — 预警名单
- POST /api/warnings/refresh — 刷新预警
- 竞赛排名算法（1,1,3,4）
- 可配置等级分段
- 自动评语生成
- 低分/偏科预警

**自检结果:** verify_stats.py 31 项测试全部通过

---

## 第5阶段：微信小程序核心页面

**状态**: ✅ 已完成

**创建文件:**
- `miniprogram/app.js` — 全局入口
- `miniprogram/app.json` — 页面路由 + tabBar
- `miniprogram/app.wxss` — 全局样式
- `miniprogram/env.js` — 环境配置
- `miniprogram/utils/` — 6 个工具模块
- `miniprogram/pages/` — 11 个页面（各 4 文件）
- `miniprogram/components/` — 6 个组件（各 4 文件）

**实现功能:**
- 登录页（角色路由跳转）
- 首页（权限动态菜单）
- 成绩录入/修改
- 成绩查询（多条件筛选、分页）
- 我的成绩（学生端）
- 统计分析（概览 + 排名）
- 预警名单
- 管理员页面（用户/课程/配置/日志）
- 统一请求封装（wx.request）
- 登录态管理

**自检结果:** app.json 包含 11 个页面路径，所有页面 js/wxml/wxss/json 齐全

---

## 第6阶段：AI 智能分析模块后端

**状态**: ✅ 已完成

**创建文件:**
- `backend/app/utils/text_sanitizer.py` — 输入清洗
- `backend/app/services/ai_prompt_builder.py` — 提示词构建
- `backend/app/services/ai_mock_service.py` — Mock 服务
- `backend/app/services/ai_provider.py` — Provider 适配器
- `backend/app/services/ai_service.py` — AI 服务主入口
- `backend/app/services/exam_analyzer.py` — 试卷分析
- `backend/app/routes/ai_routes.py` — AI 路由

**修改文件:**
- `backend/app/routes/__init__.py` — 注册 ai_bp
- `backend/app/utils/errors.py` — 添加 AI 错误码

**实现功能:**
- POST /api/ai/student-advice — 学生学习建议
- POST /api/ai/class-overview — 班级学情分析
- POST /api/ai/exam-paper/analyze — 试卷考点分析
- POST /api/ai/combined-advice — 个性化复习建议
- GET /api/ai/history — 分析历史
- Mock 模式基于真实数据动态生成
- 输入安全过滤（危险提示词检测）
- 预留 OpenAI-compatible 接口

**自检结果:** Python 语法检查全部通过，ai_bp 已注册

---

## 第7阶段：AI 智能分析小程序前端

**状态**: ✅ 已完成

**创建文件:**
- `miniprogram/pages/ai-advice/` — AI 学习建议页
- `miniprogram/pages/ai-class/` — AI 班级分析页
- `miniprogram/pages/exam-analyze/` — 试卷考点分析页
- `miniprogram/components/ai-result-card/` — AI 结果卡片组件
- `miniprogram/components/mock-badge/` — Mock 标识组件

**修改文件:**
- `miniprogram/app.json` — 添加 3 个 AI 页面路径
- `miniprogram/pages/home/index.wxml` — 添加 AI 功能入口
- `miniprogram/pages/home/index.js` — 添加 AI 权限检查
- `miniprogram/utils/permission.js` — 添加 AI 权限函数

**实现功能:**
- AI 学习建议页面（学生/教师可用）
- AI 班级分析页面（教师/管理员可用）
- 试卷考点分析页面（教师/管理员可用）
- Mock 标识组件（演示模式提示）
- AI 结果卡片组件（结构化展示）
- 首页 AI 功能入口（按权限显示）

**自检结果:** app.json 包含 14 个页面路径，所有 AI 页面文件齐全

---

## 第8阶段：文档和最终整理

**状态**: ✅ 已完成

**创建文件:**
- `docs/答辩演示流程.md` — 8-10 分钟演示流程
- `docs/测试说明.md` — 完整测试用例
- `docs/项目亮点说明.md` — 12 项亮点
- `docs/API接口清单.md` — 22 个接口文档
- `docs/部署与运行说明.md` — 部署指南
- `DEVELOPMENT_LOG.md` — 本文件
- `TODO.md` — 待办事项

**修改文件:**
- `README.md` — 最终版

**自检结果:** 所有文档已创建，README 包含完整说明

---

## 第9阶段：发布隐私、家长端与教师范围

**状态**: 已完成并有隔离回归测试

- 学生/家长只读取适用的 `published` 成绩，draft/withdrawn 不可见。
- 增加考试发布、家长绑定、家长确认及管理员维护页面。
- 增加 `teacher_class_bindings` / `teacher_course_bindings` 非破坏性迁移；成绩、导入、统计、预警、AI、发布等服务统一执行教师范围校验。
- 2026-07-11 最终复核修复家长绑定列表未初始化 `teacher_classes` 的回归，并补充教师班级过滤测试。

## 第10阶段：DeepSeek、OCR 与统一上传

**状态**: Mock/离线链路已完成；真实外部环境待人工验证

- DeepSeek 使用 Chat Completions，Key 独立读取 `DEEPSEEK_API_KEY`；结果区分 real/mock/fallback。
- 图片先真实解码和 OCR 预览，用户可修改文字后再确认 AI 分析；不把原图直接发给文本模型。
- OCR 预览按用户隔离、带 TTL，确认或失败后清理。
- 小程序统一 local/cloud 上传，后端限制 CloudBase 临时 URL 域名、HTTPS、大小和重定向。

## 第11阶段：导入批次账本与安全撤销

**状态**: 已完成并通过专项测试

- 成绩/学生 preview 不建正式账本；confirm 在同一事务中创建 UUID 批次、业务记录和安全快照条目。
- 管理员可查看批次、详情并执行快照保护的逻辑撤销。
- 人工后续修改、业务引用、管理员账号等场景自动跳过并返回原因，不物理删除账本。

## 第12阶段：按需统计、导出与 AI 反馈

**状态**: 已完成并通过专项测试

- 增加趋势、分数段、进步榜、偏科分析，重接口仅在明确筛选后按需加载。
- 增加家长待确认数量、确认表 XLSX、教师范围成绩 XLSX、学生/家长 published PDF。
- 增加角色范围内 AI 历史页面和持久化反馈，反馈前重新校验记录可见性。

## 第13阶段：部署材料与最终验证

**状态**: 代码自动验证完成；外部部署待人工执行

- Dockerfile 使用 UID/GID 10001 非 root、Gunicorn、`/api/health` 和可配置 `PORT`。
- 增加本地 Compose 与 Kubernetes ConfigMap/Secret 示例/Deployment/Service；只读根文件系统使用 `.runtime` 和 `/tmp` 卷。
- 当前结果：Python 112/112、JavaScript 43/43、JSON 38/38、pytest 26/26、运行时 19/19、统计纯函数 31/31。
- OCR Mock 两阶段通过；DeepSeek 无 Key 正确 SKIPPED；真实 PDF 2969 bytes 且文件头 `%PDF-`。
- 本机无 Docker/Kubernetes 工具，部署材料仅静态验证，未宣称实际运行。

## 第14阶段：真实环境候选版收尾

**状态**: 本地候选交付完成；外部能力按真实结果保留 FAIL/SKIPPED

- 增加仅 develop 可见的本地/云端一键切换，trial/release 固定 cloud，请求与上传动态读取模式。
- DeepSeek Key 元数据非空，单次有界真实连接因网络限制 FAIL；补齐 402/429/5xx/超时和 fallback，provider 测试 7/7。
- OCR 使用独立 Python 3.12 完成真实图片解码与 Mock 两阶段流程；RapidOCR/ONNX REAL SKIPPED。
- 最终基线：Python 113/113、JavaScript 43/43、JSON 38/38、pytest 31/31、运行时 19/19、统计 31/31、标准库 trace 49.04%。
- 生成完整候选版与 GitHub 脱敏版；CRC、禁止文件、密钥和公开版隐私扫描均通过，旧 ZIP 保留。
- Git、正式 coverage、微信工具/真机、CloudBase、Docker/Kubernetes 实际运行仍需人工或外部权限，不以 Mock/静态检查冒充完成。
