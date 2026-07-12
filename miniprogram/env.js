/**
 * 环境配置。
 * 默认始终使用 cloud；仅微信开发者工具的 develop 版本允许用本地存储覆盖。
 */
const DEFAULT_REQUEST_MODE = 'cloud';
const DEV_REQUEST_MODE_KEY = 'dev_request_mode';

function getMiniProgramEnvVersion() {
  try {
    if (typeof wx === 'undefined' || !wx.getAccountInfoSync) return '';
    const accountInfo = wx.getAccountInfoSync() || {};
    return (accountInfo.miniProgram || {}).envVersion || '';
  } catch (err) {
    return '';
  }
}

function isDevelopVersion() {
  return getMiniProgramEnvVersion() === 'develop';
}

function getRequestMode() {
  if (!isDevelopVersion()) return DEFAULT_REQUEST_MODE;
  try {
    const override = String(wx.getStorageSync(DEV_REQUEST_MODE_KEY) || '').toLowerCase();
    return override === 'local' || override === 'cloud' ? override : DEFAULT_REQUEST_MODE;
  } catch (err) {
    return DEFAULT_REQUEST_MODE;
  }
}

function setDevelopmentRequestMode(mode) {
  if (!isDevelopVersion()) return false;
  const normalized = String(mode || '').toLowerCase();
  if (normalized !== 'local' && normalized !== 'cloud') return false;
  wx.setStorageSync(DEV_REQUEST_MODE_KEY, normalized);
  return true;
}

const env = {
  // 开发版可在登录页一键覆盖；体验版/正式版固定为 cloud。
  REQUEST_MODE: getRequestMode(),
  DEFAULT_REQUEST_MODE,
  DEV_REQUEST_MODE_KEY,
  getRequestMode,
  setDevelopmentRequestMode,
  isDevelopVersion,

  // 本地 Flask 后端地址。local 模式下普通 JSON API 和文件上传都走这里。
  BASE_URL: 'http://127.0.0.1:5000',

  // 云托管默认域名仅保留给文件上传等兼容场景；普通 JSON API 在 cloud 模式下走 callContainer。
  CLOUD_BASE_URL: 'https://replace-with-your-cloud-domain.example',

  // 微信云托管配置
  CLOUD_ENV: 'replace-with-cloud-env-id',
  CONTAINER_SERVICE: 'replace-with-service-name',

  // AI 功能开关（第7阶段启用）
  AI_ENABLED: false,
};

module.exports = env;
