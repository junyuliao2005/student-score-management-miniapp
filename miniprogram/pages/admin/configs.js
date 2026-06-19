const { get, put } = require('../../utils/request');

Page({
  data: {
    configs: [],
    loading: false,
  },

  onShow() {
    this.loadData();
  },

  loadData() {
    this.setData({ loading: true });

    get('/api/configs')
      .then((data) => {
        this.setData({
          configs: data || [],
        });
      })
      .catch((err) => {
        console.error('[Configs] 加载失败:', err.message);
      })
      .finally(() => {
        this.setData({ loading: false });
      });
  },

  onValueInput(e) {
    const index = e.currentTarget.dataset.index;
    const value = e.detail.value;
    this.setData({
      [`configs[${index}].config_value`]: value,
    });
  },

  onBoolChange(e) {
    const index = e.currentTarget.dataset.index;
    this.setData({
      [`configs[${index}].config_value`]: e.detail.value ? 'true' : 'false',
    });
  },

  onSave(e) {
    const configKey = e.currentTarget.dataset.key;
    const index = e.currentTarget.dataset.index;
    const value = this.data.configs[index].config_value;

    put(`/api/configs/${configKey}`, {
      config_value: value,
    })
      .then(() => {
        wx.showToast({ title: '保存成功', icon: 'success' });
      })
      .catch((err) => {
        console.error('[Configs] 保存失败:', err.message);
      });
  },
});
