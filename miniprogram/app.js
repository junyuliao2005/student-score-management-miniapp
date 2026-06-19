const auth = require('./utils/auth');
const env = require('./env');

App({
  globalData: {
    baseUrl: env.REQUEST_MODE === 'cloud' ? env.CLOUD_BASE_URL : env.BASE_URL,
    aiEnabled: env.AI_ENABLED,
  },

  onLaunch() {
    if (env.REQUEST_MODE === 'cloud' && wx.cloud && env.CLOUD_ENV) {
      wx.cloud.init({
        env: env.CLOUD_ENV,
      });
    }

    // 检查登录态
    const token = auth.getToken();
    if (token) {
      console.log('[App] 已登录，用户:', auth.getUser());
    }
  },
});
