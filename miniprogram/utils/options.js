const { get } = require('./request');

const optionCache = {};
const loadingMap = {};
const errorMap = {};

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function fetchOptions(type, opts = {}) {
  const useCache = opts.useCache !== false;
  if (useCache && optionCache[type]) {
    return Promise.resolve({ options: optionCache[type] });
  }

  loadingMap[type] = true;
  errorMap[type] = '';

  return get('/api/options', { type: type }, { showError: false })
    .catch((err) => {
      return sleep(500).then(() => get('/api/options', { type: type }, { showError: false })
        .catch((retryErr) => {
          throw retryErr || err;
        }));
    })
    .then((data) => {
      const options = data.options || [];
      optionCache[type] = options;
      loadingMap[type] = false;
      errorMap[type] = '';
      return { options };
    })
    .catch((err) => {
      loadingMap[type] = false;
      errorMap[type] = err.message || '选项加载失败';
      throw err;
    });
}

function loadOptionMap(types) {
  const tasks = types.map((type) => fetchOptions(type)
    .then((data) => ({ type, options: data.options || [] }))
    .catch(() => ({ type, options: [] })));

  return Promise.all(tasks).then((items) => {
    const map = {};
    items.forEach((item) => {
      map[item.type] = item.options;
    });
    return map;
  });
}

function showOptionPicker(type, onSelect) {
  if (loadingMap[type]) {
    wx.showToast({ title: '正在加载选项，请稍候', icon: 'none' });
    return;
  }

  fetchOptions(type)
    .then((data) => {
      const options = data.options || [];
      if (!options.length) {
        wx.showToast({ title: '暂无可选项，可手动输入', icon: 'none' });
        return;
      }

      wx.showActionSheet({
        itemList: options.slice(0, 20).map((item) => item.label),
        success(res) {
          const selected = options[res.tapIndex];
          if (selected && onSelect) {
            onSelect(selected);
          }
        },
      });
    })
    .catch((err) => {
      wx.showToast({ title: err.message || '选项加载失败，可手动输入', icon: 'none' });
    });
}

function getOptionStatus(type) {
  return {
    loading: !!loadingMap[type],
    error: errorMap[type] || '',
    cached: !!optionCache[type],
  };
}

function clearCache(type) {
  if (type) {
    delete optionCache[type];
  } else {
    Object.keys(optionCache).forEach((key) => delete optionCache[key]);
  }
}

module.exports = {
  fetchOptions,
  loadOptionMap,
  showOptionPicker,
  getOptionStatus,
  clearCache,
};
