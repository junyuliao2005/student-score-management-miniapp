const env = require('../env');
const request = require('./request');

function uploadFile(options) {
  const state = { task: null, cancelled: false, settled: false };
  const timeoutMs = options.timeout || 60000;
  let timer = null;

  const promise = new Promise((resolve, reject) => {
    const finish = (fn, value) => {
      if (state.settled) return;
      state.settled = true;
      if (timer) clearTimeout(timer);
      fn(value);
    };
    timer = setTimeout(() => {
      if (state.task && state.task.abort) state.task.abort();
      finish(reject, new Error('文件上传超时，请重试'));
    }, timeoutMs);

    const requestMode = typeof env.getRequestMode === 'function'
      ? env.getRequestMode()
      : env.REQUEST_MODE;
    if (requestMode === 'cloud') {
      uploadViaCloudStorage(options, state)
        .then((data) => finish(resolve, data))
        .catch((err) => finish(reject, err));
      return;
    }

    uploadViaLocal(options, state)
      .then((data) => finish(resolve, data))
      .catch((err) => finish(reject, err));
  });

  return {
    promise,
    cancel() {
      state.cancelled = true;
      if (state.task && state.task.abort) state.task.abort();
    },
  };
}

function uploadViaLocal(options, state) {
  return new Promise((resolve, reject) => {
    const token = wx.getStorageSync('token') || '';
    state.task = wx.uploadFile({
      url: `${env.BASE_URL}${options.localPath}`,
      filePath: options.filePath,
      name: options.fieldName || 'file',
      formData: options.formData || {},
      header: { Authorization: token ? `Bearer ${token}` : '' },
      success(res) {
        try {
          resolve(parseBackendResponse(res));
        } catch (err) {
          reject(err);
        }
      },
      fail(err) {
        reject(new Error(state.cancelled ? '上传已取消' : (err.errMsg || '文件上传失败')));
      },
    });
    bindProgress(state.task, options.onProgress);
  });
}

function uploadViaCloudStorage(options, state) {
  if (!wx.cloud || !wx.cloud.uploadFile || !wx.cloud.getTempFileURL) {
    return Promise.reject(new Error('当前微信基础库不支持云存储上传'));
  }
  const ext = getExtension(options.fileName || options.filePath);
  const kind = String(options.cloudKind || 'files').replace(/[^a-z0-9_-]/gi, '');
  const cloudPath = `private-uploads/${kind}/${Date.now()}-${randomId()}.${ext}`;
  let fileID = '';

  return new Promise((resolve, reject) => {
    state.task = wx.cloud.uploadFile({
      cloudPath,
      filePath: options.filePath,
      success(res) { resolve(res); },
      fail(err) { reject(new Error(state.cancelled ? '上传已取消' : (err.errMsg || '云存储上传失败'))); },
    });
    bindProgress(state.task, options.onProgress);
  })
    .then((res) => {
      fileID = res.fileID;
      return wx.cloud.getTempFileURL({ fileList: [fileID] });
    })
    .then((res) => {
      const item = (res.fileList || [])[0] || {};
      if (!item.tempFileURL) throw new Error('无法获取云存储临时地址');
      return request.post(options.cloudPath, {
        file_id: fileID,
        temp_url: item.tempFileURL,
        file_name: options.fileName || `upload.${ext}`,
      }, { showError: false });
    })
    .finally(() => {
      if (fileID && wx.cloud.deleteFile) {
        wx.cloud.deleteFile({ fileList: [fileID] }).catch(() => {});
      }
    });
}

function parseBackendResponse(res) {
  let body = res.data;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (err) { throw new Error('服务端响应解析失败'); }
  }
  if (res.statusCode !== 200 || !body || body.code !== 0) {
    throw new Error((body && body.message) || `上传失败(${res.statusCode})`);
  }
  return body.data;
}

function bindProgress(task, callback) {
  if (callback && task && task.onProgressUpdate) {
    task.onProgressUpdate((res) => callback(res.progress || 0));
  }
}

function getExtension(name) {
  const match = String(name || '').toLowerCase().match(/\.([a-z0-9]+)$/);
  return match ? match[1] : 'bin';
}

function randomId() {
  return `${Math.random().toString(36).slice(2, 10)}${Math.random().toString(36).slice(2, 10)}`;
}

module.exports = { uploadFile };
