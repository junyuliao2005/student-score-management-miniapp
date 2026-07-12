const auth = require('./utils/auth');
const env = require('./env');

function getRequestMode() {
  return typeof env.getRequestMode === 'function'
    ? env.getRequestMode()
    : env.REQUEST_MODE;
}

function initCloudIfNeeded() {
  if (getRequestMode() === 'cloud' && wx.cloud && env.CLOUD_ENV) {
    wx.cloud.init({
      env: env.CLOUD_ENV,
    });
  }
}

App({
  globalData: {
    baseUrl: getRequestMode() === 'cloud' ? env.CLOUD_BASE_URL : env.BASE_URL,
    requestMode: getRequestMode(),
    aiEnabled: env.AI_ENABLED,
  },

  onLaunch() {
    initCloudIfNeeded();

    // 检查登录态
    const token = auth.getToken();
    if (token) {
      console.log('[App] 已登录，用户:', auth.getUser());
    }
  },

  refreshRequestMode() {
    const mode = getRequestMode();
    this.globalData.requestMode = mode;
    this.globalData.baseUrl = mode === 'cloud' ? env.CLOUD_BASE_URL : env.BASE_URL;
    initCloudIfNeeded();
    return mode;
  },
});
