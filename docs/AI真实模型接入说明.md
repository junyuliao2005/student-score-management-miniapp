# AI 真实模型接入说明

当前系统默认使用 `mock` 模式，适合体验版演示、课程设计答辩和稳定测试。本轮不接入真实大模型，也不把 `AI_MOCK_ENABLED` 改为 `false`。

## 安全原则

- API Key 只能配置在 Flask 后端环境变量中。
- 小程序前端不能保存、传递或硬编码 API Key。
- 微信云托管中修改 AI 环境变量后需要重新发布后端服务。
- 如果真实 API 不可用且 `AI_MOCK_ENABLED=true`，系统可以继续用 mock 演示。

## OpenAI-compatible 示例

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

## 视觉模型说明

试卷图片视觉分析是否能真实启用，取决于所选模型是否支持图像输入。如果模型不支持图片输入，建议继续保持 mock，或后续配置支持多模态的 OpenAI-compatible vision provider。

视觉配置预留：

```env
AI_VISION_PROVIDER=openai_compatible_vision
AI_VISION_API_BASE_URL=
AI_VISION_API_KEY=
AI_VISION_MODEL=
AI_VISION_TIMEOUT=60
AI_VISION_MAX_IMAGE_MB=10
```

## 回退建议

答辩和体验版阶段建议保持：

```env
AI_PROVIDER=mock
AI_MOCK_ENABLED=true
```

这样无需外部网络和 API 额度，AI 学情分析仍能稳定演示。
