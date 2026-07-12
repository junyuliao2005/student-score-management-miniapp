# CloudBase 预发布步骤

本轮没有修改云端环境变量、部署服务或上传体验版。以下步骤必须由具有微信/CloudBase 权限的用户人工执行。

## 1. 发布前准备

1. 备份云端 MySQL，确认备份可下载且非空。
2. 对云端数据库只执行缺失的幂等迁移，不运行 `init_db.py`。
3. 配置教师班级/课程范围；迁移后的空绑定会默认返回空数据。
4. 确认云端环境变量存在强随机 `SECRET_KEY`、`JWT_SECRET_KEY` 和数据库凭据。
5. 默认保留 `AI_PROVIDER=mock`；只有准备做有界真实测试时才设置后端 `DEEPSEEK_API_KEY`。

### 云数据库备份命令模板

先在本机环境变量中填写云数据库连接信息，不要把密码写入脚本或命令历史。以下命令只生成备份，不执行迁移：

```powershell
$mysqlBin = 'C:\path\to\mysql\bin'
$backupDir = $env:CLOUD_BACKUP_DIR
if ([string]::IsNullOrWhiteSpace($backupDir)) { throw 'Set CLOUD_BACKUP_DIR to a protected directory outside the repository' }
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
$clientFile = Join-Path $env:TEMP ("cloud-mysql-" + [guid]::NewGuid().ToString('N') + '.cnf')
$dumpFile = Join-Path $backupDir ("student_grade_db-" + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.sql')
$errorFile = "$dumpFile.stderr"
try {
  @"
[client]
host=$env:CLOUD_DB_HOST
port=$env:CLOUD_DB_PORT
user=$env:CLOUD_DB_USER
password=$env:CLOUD_DB_PASSWORD
"@ | Set-Content -LiteralPath $clientFile -Encoding ASCII
  $args = @("--defaults-extra-file=$clientFile", '--single-transaction', '--quick', '--routines', '--triggers', '--events', '--hex-blob', '--no-tablespaces', $env:CLOUD_DB_NAME)
  $process = Start-Process -FilePath (Join-Path $mysqlBin 'mysqldump.exe') -ArgumentList $args -NoNewWindow -Wait -PassThru -RedirectStandardOutput $dumpFile -RedirectStandardError $errorFile
  if ($process.ExitCode -ne 0 -or (Get-Item $dumpFile).Length -eq 0) { throw 'Cloud MySQL backup failed' }
  Get-FileHash -Algorithm SHA256 -LiteralPath $dumpFile
} finally {
  Remove-Item -LiteralPath $clientFile -Force -ErrorAction SilentlyContinue
}
```

`cloud-backups/` 必须保存在项目外或受控敏感目录，不进入 Git、Docker 构建上下文或交付 ZIP。

## 2. 后端预发布

1. 建议创建独立预发布服务 `replace-with-service-name-rc`，不覆盖 `replace-with-service-name` 稳定服务；若平台限制只能使用同一服务，则必须保留上一可回滚版本。
2. 容器端口为 5000，健康检查 `/api/health`。
3. 发布后先验证健康检查和日志，无数据库密码、Token、Key 或完整 Prompt。
4. 使用自有测试凭据验证四角色登录和普通 JSON API。
5. 一个账号查看统计时，另一个账号验证登录和“我的成绩”，观察 Gunicorn 超时。

## 3. 小程序云模式

1. 默认配置为 cloud；体验版/正式版会忽略开发版本地覆盖，不需要改 `REQUEST_MODE`。
2. 核对 `CLOUD_ENV` 和 `CONTAINER_SERVICE`，普通 JSON API 应走 `wx.cloud.callContainer`。
3. 不把云托管默认域名配置为正式 request 合法域名。
4. 清缓存、编译并上传新的体验版本；不要直接提交正式审核。

## 4. CloudBase 私有上传

1. 云存储规则限制登录用户只读写自己的 `private-uploads/` 临时文件。
2. 成绩 Excel、学生 Excel、试卷图片分别验证 `uploadFile -> getTempFileURL -> callContainer -> 后端消费 -> deleteFile`。
3. 后端只允许配置中的 CloudBase HTTPS 域名，拒绝 HTTP、凭据 URL、重定向和超大响应。
4. 处理完成后确认云临时文件被删除；失败时也检查清理。

## 5. DeepSeek 有界验证

仅当 Key、费用和授权均已确认：连接 1 次、结构化输出 1 次、学生建议 1 次、试卷文本 1 次。结果必须为 `provider=deepseek`、`mode=real`、模型正确且有 usage；任何失败不得伪装成 real。

## 6. 回滚条件

健康检查失败、迁移异常、权限越界、CloudBase 任意 URL 下载、日志泄密或连续 worker timeout 时停止预发布，切回稳定版本；不得清空数据库或强制覆盖。

## 7. 迁移顺序与回滚

1. 只在独立预发布数据库或已完成可恢复备份后执行。
2. 先执行既有家长/发布和留言迁移，再依次运行 `add_teacher_bindings_tables.py`、`add_import_batch_tables.py`、`add_ai_feedback_table.py`。
3. 每一步检查目标表、列、索引和外键，再幂等复跑一次；严禁运行 `init_db.py`。
4. 迁移失败时停止部署并恢复数据库备份；应用失败但迁移成功时，回切稳定容器版本，不删除新表。
5. 完成 health、四角色权限、普通 JSON API、三个私有上传链路后，才将体验版指向预发布服务。
