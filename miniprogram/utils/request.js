/**
 * 网络请求封装
 * 统一处理本地 wx.request / 云托管 callContainer、Authorization、trace_id、业务错误
 */
const env = require('../env');

const BASE_URL = env.BASE_URL;
const CLOUD_BASE_URL = env.CLOUD_BASE_URL || env.BASE_URL;
const CLOUD_ENV = env.CLOUD_ENV;
const CONTAINER_SERVICE = env.CONTAINER_SERVICE;

function isFullUrl(url) {
  return /^https?:\/\//i.test(url);
}

function isCloudMode() {
  const mode = typeof env.getRequestMode === 'function'
    ? env.getRequestMode()
    : env.REQUEST_MODE;
  return mode === 'cloud';
}

function getActiveBaseUrl() {
  return isCloudMode() ? CLOUD_BASE_URL : BASE_URL;
}

/**
 * 生成 trace_id
 */
function generateTraceId() {
  const timestamp = Date.now().toString(36);
  const random = Math.random().toString(36).substring(2, 10);
  return `${timestamp}-${random}`;
}

/**
 * 统一处理后端响应
 */
function handleResponse(res, showError, resolve, reject, context = {}) {
  if (res.statusCode === 200) {
    const body = res.data;
    if (body && body.code === 0) {
      resolve(body.data);
    } else {
      const errMsg = (body && body.message) || '请求失败';
      console.error(`[Request] 业务错误: ${errMsg}`, {
        ...context,
        traceId: (body && body.trace_id) || context.traceId,
        body,
      });

      if (body && (body.code === 40001 || body.code === 40002 || body.code === 40003)) {
        handleAuthExpired();
        reject(new Error(errMsg));
        return;
      }

      if (showError) {
        wx.showToast({
          title: errMsg,
          icon: 'none',
          duration: 2000,
        });
      }
      reject(new Error(errMsg));
    }
  } else if (res.statusCode === 401) {
    handleAuthExpired();
    reject(new Error('未授权'));
  } else {
    const errMsg = `请求失败(${res.statusCode})`;
    console.error('[Request] HTTP错误:', {
      ...context,
      statusCode: res.statusCode,
      traceId: (res.data && res.data.trace_id) || context.traceId,
      body: res.data,
    });
    if (showError) {
      wx.showToast({
        title: errMsg,
        icon: 'none',
        duration: 2000,
      });
    }
    reject(new Error(errMsg));
  }
}

function handleAuthExpired() {
  wx.removeStorageSync('token');
  wx.removeStorageSync('user');
  wx.removeStorageSync('roles');
  wx.removeStorageSync('permissions');
  wx.showToast({
    title: '登录已过期，请重新登录',
    icon: 'none',
    duration: 2000,
  });
  setTimeout(() => {
    wx.reLaunch({ url: '/pages/login/index' });
  }, 1500);
}

/**
 * 封装普通 JSON API 请求。
 * local 模式使用 wx.request + BASE_URL，cloud 模式使用 wx.cloud.callContainer。
 * @param {Object} options
 * @param {string} options.url - 接口路径（如 /api/auth/login）
 * @param {string} options.method - 请求方法 GET/POST/PUT/DELETE
 * @param {Object} options.data - 请求数据
 * @param {Object} options.header - 额外请求头
 * @param {boolean} options.showError - 是否自动显示错误提示（默认 true）
 * @returns {Promise<Object>} 返回 data 字段
 */
function request(options) {
  const {
    url,
    method = 'GET',
    data = {},
    header = {},
    showError = true,
  } = options;

  return new Promise((resolve, reject) => {
    const token = wx.getStorageSync('token') || '';
    const traceId = generateTraceId();

    const fullUrl = isFullUrl(url);
    const path = fullUrl ? url : url;
    const mode = isCloudMode() && !fullUrl ? 'cloud' : 'local';
    const context = {
      mode,
      path,
      method,
      traceId,
    };
    const requestHeader = {
      'content-type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : '',
      'X-Trace-Id': traceId,
      ...header,
    };

    if (isCloudMode() && !fullUrl && wx.cloud && wx.cloud.callContainer && CLOUD_ENV && CONTAINER_SERVICE) {
      wx.cloud.callContainer({
        config: {
          env: CLOUD_ENV,
        },
        path: path,
        method: method,
        data: data,
        header: {
          'X-WX-SERVICE': CONTAINER_SERVICE,
          ...requestHeader,
        },
        success(res) {
          handleResponse(res, showError, resolve, reject, context);
        },
        fail(err) {
          console.error('[Request] callContainer 网络错误:', {
            mode,
            path,
            method,
            errMsg: err.errMsg || err.message || String(err),
            traceId,
            err,
          });
          const errMsg = '网络连接失败，请检查网络';
          if (showError) {
            wx.showToast({
              title: errMsg,
              icon: 'none',
              duration: 2000,
            });
          }
          reject(new Error(errMsg));
        },
      });
      return;
    }

    const requestUrl = fullUrl ? url : `${getActiveBaseUrl()}${url}`;
    wx.request({
      url: requestUrl,
      method: method,
      data: data,
      header: requestHeader,
      success(res) {
        handleResponse(res, showError, resolve, reject, context);
      },
      fail(err) {
        console.error('[Request] wx.request 网络错误:', {
          ...context,
          url: requestUrl,
          errMsg: err.errMsg || err.message || String(err),
          err,
        });
        const errMsg = '网络连接失败，请检查网络';
        if (showError) {
          wx.showToast({
            title: errMsg,
            icon: 'none',
            duration: 2000,
          });
        }
        reject(new Error(errMsg));
      },
    });
  });
}

/**
 * GET 请求
 */
function get(url, data, options = {}) {
  return request({ url, method: 'GET', data, ...options });
}

/**
 * POST 请求
 */
function post(url, data, options = {}) {
  return request({ url, method: 'POST', data, ...options });
}

/**
 * PUT 请求
 */
function put(url, data, options = {}) {
  return request({ url, method: 'PUT', data, ...options });
}

/**
 * DELETE 请求
 */
function del(url, data, options = {}) {
  return request({ url, method: 'DELETE', data, ...options });
}

module.exports = {
  request,
  get,
  post,
  put,
  del,
  BASE_URL: getActiveBaseUrl(),
};
