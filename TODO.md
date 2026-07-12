# 待办事项

本文件只保留当前代码尚未自动完成、必须依赖外部环境或属于后续增强的事项。已完成的教师范围、家长端、OCR 两阶段、导入批次撤销、统计扩展、导出和 AI 历史不再列为待办。

## 交付前人工操作

1. **安装当前依赖**：项目 `.venv` 尚未安装 Pillow、ReportLab、coverage 和 pytest-cov。当前网络索引受限，恢复后执行 `cd backend && .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt`。
2. **其他环境增量迁移**：本地 MySQL 已完成备份和 5 张表迁移。云端或其他数据库仍必须各自先备份、检查缺失表，再运行幂等脚本；严禁运行 `init_db.py`。
3. **教师授权**：迁移后由管理员维护教师班级和课程范围；未绑定教师默认拒绝访问全校数据。
4. **微信开发者工具和真机**：编译 43 个小程序 JS 文件对应页面，验证 local/cloud 请求、文件选择、Base64 文件打开及角色导航。
5. **云端上传链路**：使用真实 AppID/CloudBase 权限验证 `wx.cloud.uploadFile -> callContainer -> 后端消费 -> deleteFile`，并检查私有目录安全规则。
6. **真实 OCR/DeepSeek**：RapidOCR 使用单独 Python 3.11/3.12 环境；DeepSeek Key 已配置但本轮单次真实连接受网络阻断。恢复网络后仍只做有界测试，不得把 Key 放入源码或小程序。
7. **容器与 Kubernetes**：本机无 Docker、Compose、kubectl、Kind、Minikube；需要在具备工具的环境实际构建、启动和探针验证。
8. **Git 基线**：当前 `.git` 不完整，需按 `docs/GIT待执行操作.md` 人工建立本地基线；不要提交 `.env`、真实数据、运行时缓存或交付 ZIP。
9. **原始 Word/PPT 交付物**：代码和 Markdown 文档已更新，原始课程设计 Word/PDF/PPT 尚需人工核对版式和内容一致性。

## 可选工程增强

- 安装 `pytest-cov` 并形成正式覆盖率门槛和 HTML 报告。
- 增加 CI，在隔离 SQLite 环境运行语法、pytest、密钥扫描和迁移静态检查。
- 为导入批次增加管理员导出审计报告、后台异步大文件处理和更细粒度审批。
- 增加课程批量导入 preview/confirm；继续完善宽表字段映射修正和错误行下载。
- 对趋势和分布接入合规的小程序图表组件，当前实现保持轻量列表/条形展示。
- 增加审计日志归档策略、备份恢复演练和并发压测。
- 在真实 DeepSeek 或 OCR 启用前完成隐私评估、费用上限、超时和降级演练。

## 当前已知限制

- Docker/Kubernetes 只完成静态材料，未在本机真实运行。
- DeepSeek 单次真实连接为 `category=network`，尚无 REAL PASS；离线错误分类和 fallback 已通过。
- RapidOCR 真实推理未验证；MockOCR 两阶段流程已自动通过。
- 云托管、微信体验版和云端 MySQL 迁移仍需要人工权限；本地 MySQL 迁移与只读 HTTP 验收已完成。
