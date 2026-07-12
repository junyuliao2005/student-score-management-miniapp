# AI 真实模型接入说明

DeepSeek V4 Pro 的当前实现、固定 Chat Completions 地址、重试、结构化输出和 fallback 规则见 `docs/DeepSeek-V4-Pro接入说明.md`。当前推荐使用 `AI_PROVIDER=deepseek`；旧的 `openai_compatible` 配置仅为兼容已有部署保留。

当前系统默认使用 `mock` 模式，适合体验版演示、课程设计答辩和稳定测试。本轮不接入真实大模型，也不把 `AI_MOCK_ENABLED` 改为 `false`。

## 安全原则

- API Key 只能配置在 Flask 后端环境变量中。
- 小程序前端不能保存、传递或硬编码 API Key。
- 微信云托管中修改 AI 环境变量后需要重新发布后端服务。
- 如果真实 API 不可用且 `AI_MOCK_ENABLED=true`，系统可以继续用 mock 演示。

## 兼容 Provider 示例

```env
AI_PROVIDER=openai_compatible
AI_API_BASE_URL=https://api.deepseek.com
AI_API_KEY=your_api_key
AI_MODEL=deepseek-v4-flash
AI_MOCK_ENABLED=false
```

## 通义千问 DashScope 示例

```env
AI_PROVIDER=openai_compatible
AI_API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
AI_API_KEY=your_dashscope_api_key
AI_MODEL=qwen-plus
AI_MOCK_ENABLED=false
```

## 试卷图片链路

当前正式设计不是把图片直接发送给 DeepSeek-V4-Pro，而是：安全上传 -> 图片真实解码 -> OCR 预览 -> 用户修改文字 -> 确认 -> 脱敏 -> DeepSeek/Mock/Fallback 结构化分析。这样即使文本模型不支持视觉输入，也能提供可审查的识别中间结果。

- `OCR_PROVIDER=mock`：自动测试和稳定演示，不冒充真实识别。
- `OCR_PROVIDER=local`：在 Python 3.11/3.12 可选环境安装 RapidOCR 后启用。
- DeepSeek 只接收确认后的文字，不接收原始图片。
- OCR 预览按当前用户隔离、带 TTL，确认或失败后清理。

## 回退建议

答辩和体验版阶段建议保持：

```env
AI_PROVIDER=mock
AI_MOCK_ENABLED=true
```

这样无需外部网络和 API 额度，AI 学情分析仍能稳定演示。所有结果明确返回 `provider`、`model`、`mode=real|mock|fallback`、`trace_id`、`generated_at` 和 `usage`，Mock/Fallback 不冒充真实模型。
