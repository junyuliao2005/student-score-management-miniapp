# GitHub 上传指南（第一次上传版）

这份指南适合第一次使用 GitHub 的同学。你可以先用“网页上传法”，最简单；熟悉以后再学 Git 命令行。

## 方法一：GitHub 网页上传（最简单，推荐第一次用）

### 1. 注册 / 登录 GitHub

打开 GitHub 官网并登录账号。

### 2. 新建仓库

点击右上角 `+` -> `New repository`。

建议填写：

- Repository name：`student-score-management-miniapp`
- Description：`微信小程序 + Flask + MySQL 的学生成绩管理与 AI 学情诊断辅助系统`
- Public / Private：先选 `Private`，检查无误后再改成 `Public`
- 不要勾选 `Add a README file`，因为压缩包里已经有 README

然后点击 `Create repository`。

### 3. 解压本压缩包

把 `student-score-management-miniapp-github-ready.zip` 解压，进入里面的文件夹。

你应该能看到：

```text
backend/
miniprogram/
docs/
screenshots/
README.md
.gitignore
GITHUB_UPLOAD_GUIDE.md
```

### 4. 网页上传文件

进入你刚创建的 GitHub 仓库页面：

1. 点击 `uploading an existing file`
2. 把解压后的所有文件和文件夹拖进去
3. 等待上传完成
4. 在底部 Commit message 写：`Initial project upload`
5. 点击 `Commit changes`

如果网页提示文件太多，可以分几次上传：

1. 先上传 `README.md`、`.gitignore`、`GITHUB_UPLOAD_GUIDE.md`
2. 再上传 `backend/`
3. 再上传 `miniprogram/`
4. 最后上传 `docs/` 和 `screenshots/`

### 5. 检查敏感信息

上传后，在 GitHub 仓库页面搜索这些关键词，确认没有真实信息：

```text
DB_PASSWORD
API_KEY
SECRET
CLOUD_ENV
CONTAINER_SERVICE
appid
AppSecret
cloudbase
```

重点看搜索结果中是否出现你的真实密码、真实 API Key、真实 AppID、真实云环境 ID。模板里的 `your_mysql_password`、`AI_API_KEY=` 这类占位内容是正常的。


### 6. 改成公开仓库

确认没有敏感信息后：

`Settings` -> `General` -> 页面最底部 `Danger Zone` -> `Change repository visibility` -> 改为 `Public`。

然后把仓库链接放到简历里，例如：

```text
GitHub: https://github.com/你的用户名/student-score-management-miniapp
```

---

## 方法二：GitHub Desktop 上传（适合不想用命令行）

1. 安装 GitHub Desktop。
2. 登录你的 GitHub 账号。
3. 点击 `File` -> `Add local repository`。
4. 选择解压后的项目文件夹。
5. 如果提示不是 Git 仓库，点击 `create a repository`。
6. 填写仓库名 `student-score-management-miniapp`。
7. 点击 `Publish repository`。
8. 第一次建议先不要勾选 Public，先作为 Private 发布。

---

## 方法三：Git 命令行上传（以后可以学）

在解压后的项目目录中打开终端：

```bash
git init
git add .
git commit -m "Initial project upload"
git branch -M main
git remote add origin https://github.com/你的用户名/student-score-management-miniapp.git
git push -u origin main
```

如果 GitHub 要求登录，按提示登录即可。现在 GitHub 通常不再使用账号密码推送，而是使用浏览器授权或 Personal Access Token。

---

## 上传后 README 还要补什么？

建议你之后补 6 张截图到 `screenshots/` 目录：

- `login.png`
- `teacher-home.png`
- `score-list.png`
- `stats.png`
- `student-score.png`
- `ai-analysis.png`

截图补好后，在 README 里加一段：

```md
## 项目截图

![登录页](screenshots/login.png)
![成绩查询](screenshots/score-list.png)
![统计分析](screenshots/stats.png)
![AI 学情分析](screenshots/ai-analysis.png)
```

注意：截图中不要出现真实姓名、真实学号、真实成绩、手机号等隐私信息。
