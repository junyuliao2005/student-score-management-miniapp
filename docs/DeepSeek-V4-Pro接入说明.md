# DeepSeek V4 Pro 接入说明

## 定位

DeepSeek 仅作为本项目 Flask 后端的 AI Provider，不影响 Codex 或小程序运行环境。小程序不保存 API Key，所有请求经后端鉴权、数据整理和脱敏后发起。

## 配置

在 `backend/.env` 或云托管环境变量中配置：

```env
AI_PROVIDER=deepseek
AI_FALLBACK_ENABLED=true
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_CHAT_ENDPOINT=/chat/completions
DEEPSEEK_API_KEY=replace-with-your-secret
DEEPSEEK_MODEL=deepseek-v4-pro
DEEPSEEK_THINKING_ENABLED=true
DEEPSEEK_REASONING_EFFORT=max
AI_TIMEOUT_SECONDS=90
AI_MAX_RETRIES=2
```

最终调用地址固定为：

```text
https://api.deepseek.com/chat/completions
```

代码不使用 `/responses`，也不使用 `OPENAI_API_KEY` 保存 DeepSeek Key。

## 请求与安全

- 请求使用 Chat Completions 格式。
- 请求体包含 `thinking={"type":"enabled"}`、`reasoning_effort="max"` 和 `response_format={"type":"json_object"}`。
- 外部调用前执行学生姓名匿名化、手机号/身份证/token/password/API key 脱敏。
- 只读取最终 `message.content`；`reasoning_content` 不保存、不展示、不写日志。
- 日志不记录 Authorization、API Key、完整 prompt 或响应正文。

## 失败与降级

- 最多两次有限重试，采用 0.5 秒、1 秒指数退避。
- 401：鉴权失败，不重试。
- 402：额度不足，不重试。
- 429、网络错误、超时、5xx：有限重试。
- 非 JSON 和非正常 `finish_reason` 视为无效结果。
- `AI_FALLBACK_ENABLED=true` 时回退本地 Mock，并返回 `mode=fallback`。
- `AI_FALLBACK_ENABLED=false` 时返回明确业务错误。

## 响应来源标识

所有 AI 结果包含：

```text
provider
model
mode: real | mock | fallback
trace_id
generated_at
usage
is_mock
```

## 验证

无 Key 时脚本安全跳过：

```bash
cd backend
python scripts/test_deepseek_connection.py
python scripts/test_deepseek_structured_output.py
```

配置 Key 后，每个脚本只执行一次最小请求，不循环消耗额度，且不会打印 Key。

