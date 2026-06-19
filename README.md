# 学生成绩管理小程序 + AI 学情诊断辅助系统

一个基于 **微信小程序 + Python Flask + MySQL** 的学生成绩管理与学情分析系统。项目面向学生、教师、管理员和家长等角色，支持成绩录入、成绩查询、统计分析、排名展示、低分预警、师生留言、Excel 批量导入、成绩发布与家长确认等功能，并提供 AI 学情分析、班级分析和试卷考点分析的演示模块。

> 说明：本仓库为课程设计 / 个人实践项目的公开展示版，已删除敏感配置、私有云环境信息和真实数据，仅保留脱敏后的核心代码、文档和本地运行说明。

## 项目亮点

- **前后端分离**：微信小程序原生前端 + Flask REST API 后端，前后端通过 JSON 接口通信。
- **多角色权限**：支持学生、教师、管理员、家长等角色，使用 JWT 登录认证和简化 RBAC 权限控制。
- **成绩管理闭环**：覆盖成绩录入、查询、统计、排名、发布、家长查看与确认等流程。
- **统计分析能力**：支持总分、平均分、班级排名、年级排名、单科排名、荣誉榜、低分/偏科预警。
- **Excel 导入流程**：支持学生基础信息和成绩数据批量导入，采用“预览校验 -> 确认写入”的流程，降低数据污染风险。
- **AI 演示模块**：默认 mock 模式，无需外部 API Key，可基于成绩数据生成学习建议、班级分析和试卷考点分析演示结果。
- **工程化文档**：包含 README、API 接口清单、测试说明、部署说明、项目亮点说明和答辩演示路线。

## 技术栈

| 模块 | 技术 |
|---|---|
| 前端 | 微信小程序原生开发、JavaScript、WXML、WXSS |
| 后端 | Python、Flask、Flask-SQLAlchemy、Flask-CORS |
| 数据库 | MySQL、InnoDB、SQL |
| 认证权限 | JWT、RBAC |
| Excel 处理 | openpyxl |
| AI 模块 | Mock 模式、OpenAI-compatible API 预留 |
| 工程文档 | Markdown、接口文档、测试说明、答辩路线 |

## 功能模块

### 学生端

- 查看个人成绩
- 按学期、考试批次、课程筛选成绩
- 查看总分、平均分、班级排名、年级排名和薄弱科目提示
- 查看 AI 个性化学习建议
- 与教师进行留言沟通

### 教师端

- 录入、修改、查询成绩
- 按班级、学生、课程、学期、考试批次筛选成绩
- 查看成绩统计、总分排名、单科排名、荣誉榜
- 发布或撤回考试成绩
- 查看低分预警和偏科预警
- 进行班级学情分析和试卷考点分析

### 管理员端

- 管理用户、课程、系统配置
- 批量导入学生基础信息
- 查看审计日志
- 维护成绩显示与发布相关配置

### 家长端

- 绑定学生
- 查看已发布成绩
- 根据发布设置查看分数、排名、统计信息
- 对成绩进行签名确认

## 目录结构

```text
student-score-management-miniapp/
├── backend/                  # Flask 后端工程
│   ├── app.py                # 启动入口
│   ├── config.py             # 配置类
│   ├── requirements.txt      # Python 依赖
│   ├── .env.example          # 环境变量模板
│   ├── app/
│   │   ├── models/           # ORM 模型
│   │   ├── routes/           # API 路由
│   │   ├── services/         # 业务逻辑
│   │   ├── middleware/       # JWT、权限、错误处理
│   │   └── utils/            # 工具函数
│   ├── scripts/              # 初始化、演示数据、验证脚本
│   └── sql/                  # 数据库 DDL 与配置数据
├── miniprogram/              # 微信小程序前端工程
│   ├── pages/                # 页面
│   ├── components/           # 公共组件
│   ├── utils/                # 请求、权限、格式化等工具
│   └── env.js                # 本地环境配置
├── docs/                     # 项目文档
├── screenshots/              # 项目截图占位目录
├── .gitignore
└── README.md
```

## 本地运行

### 1. 环境准备

- Python 3.9+
- MySQL 8.0+
- 微信开发者工具

### 2. 启动后端

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
```

编辑 `backend/.env`，填写本地 MySQL 配置：

```env
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=student_grade_db
AI_PROVIDER=mock
AI_MOCK_ENABLED=true
```

初始化数据库并填充演示数据：

```bash
python scripts/init_db.py
python scripts/seed_demo.py
python app.py
```

启动后访问：

```text
http://127.0.0.1:5000/api/health
```

### 3. 启动小程序

1. 打开微信开发者工具。
2. 选择“导入项目”。
3. 项目目录选择 `miniprogram/`。
4. AppID 可选择测试号，或使用游客模式。
5. 本地联调时勾选“不校验合法域名”。
6. 确认 `miniprogram/env.js` 中：

```js
REQUEST_MODE: 'local',
BASE_URL: 'http://127.0.0.1:5000'
```

## 默认演示账号

| 角色 | 用户名 | 密码 |
|---|---|---|
| 管理员 | admin01 | 123456 |
| 教师 | teacher01 | 123456 |
| 学生 | student01 | 123456 |
| 家长 | parent01 | 123456 |

> 演示账号由初始化或 seed 脚本创建，具体以本地脚本实际生成结果为准。

## AI 模块说明

本项目默认使用 mock 模式，不需要外部 API Key：

- 学生学习建议：基于真实成绩数据生成优势科目、薄弱科目和复习建议。
- 班级学情分析：统计班级平均分、及格率、优秀率和薄弱科目。
- 试卷考点分析：根据试卷文本关键词生成考点分析和复习建议。
- 试卷图片分析：保留视觉模型接口，公开版默认使用演示模式。

如需接入真实大模型服务，可参考 `docs/AI真实模型接入说明.md`，并在 `.env` 中配置自己的 API Key。不要把真实 API Key 提交到 GitHub。

## 主要文档

- `docs/API接口清单.md`
- `docs/测试说明.md`
- `docs/部署与运行说明.md`
- `docs/项目亮点说明.md`
- `docs/智能Excel适配器说明.md`
- `docs/隐私保护与数据安全设计.md`
- `docs/答辩演示路线.md`

## 隐私与安全说明

公开仓库已删除：

- `.env` 真实环境变量文件
- 微信开发者工具私有配置文件
- 云托管环境 ID、服务名、私有部署地址
- 真实学生信息、真实成绩数据和 Excel 原始数据
- 数据库密码、API Key、App Secret 等敏感信息

如果你基于本项目继续开发，请只提交 `.env.example`，不要提交 `.env`。

## 简历写法参考

```text
学生成绩管理小程序 + AI 学情诊断辅助系统｜个人项目 / 课程设计项目
技术栈：微信小程序、JavaScript、Python、Flask、MySQL、JWT、RBAC、openpyxl
- 基于微信小程序实现学生、教师、管理员、家长等多角色页面，完成成绩查询、成绩录入、统计分析、师生留言等功能。
- 使用 Flask 搭建后端服务，设计成绩、用户、课程、权限、留言、成绩发布等业务模块，并完成前后端接口联调。
- 实现成绩统计、班级排名、年级排名、单科排名、荣誉榜、低分预警和偏科预警等功能。
- 实现 Excel 批量导入预览与确认流程，支持错误行识别、重复行提示和标准导入数据生成。
- 编写 README、API 文档、测试说明和答辩演示路线，完成项目展示材料整理。
```

## 未来优化方向

- 增加更完整的单元测试和接口自动化测试。
- 补充项目截图和 1-2 分钟演示视频。
- 将 AI 模块从 mock 模式升级为真实模型调用。
- 增加更细粒度的教师任课范围控制。
- 优化小程序 UI 和移动端表格展示体验。
