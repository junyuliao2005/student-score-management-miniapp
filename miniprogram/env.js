/**
 * 环境配置（公开仓库脱敏版）
 *
 * 本地开发默认使用 local 模式，通过 BASE_URL 调用 Flask 后端。
 * 如需微信云托管，请在自己的私有配置中填写 CLOUD_ENV、CONTAINER_SERVICE、CLOUD_BASE_URL。
 */
const env = {
  REQUEST_MODE: 'local',
  BASE_URL: 'http://127.0.0.1:5000',

  // 以下字段保留为空，避免公开个人云环境信息
  CLOUD_BASE_URL: '',
  CLOUD_ENV: '',
  CONTAINER_SERVICE: '',

  AI_ENABLED: false,
};

module.exports = env;
