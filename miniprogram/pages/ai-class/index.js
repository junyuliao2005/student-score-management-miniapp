const { get, post } = require('../../utils/request');
const options = require('../../utils/options');

Page({
  data: {
    className: '',
    classOptions: [],
    classIndex: 0,
    classesLoading: false,
    term: '2025-2026-2',
    loading: false,
    result: null,
    errorMsg: '',
  },

  onLoad() {
    this.loadClasses();
  },

  loadClasses() {
    this.setData({ classesLoading: true, errorMsg: '' });

    options.fetchOptions('classes')
      .then((data) => {
        const classOptions = data.options || [];
        this.setData({
          classOptions: classOptions,
          classIndex: 0,
        });
      })
      .catch((err) => {
        return get('/api/classes')
          .then((data) => {
            const classOptions = (data.classes || []).map((item) => ({
              label: item,
              value: item,
            }));
            this.setData({ classOptions });
          })
          .catch(() => {
            this.setData({ errorMsg: err.message || '班级列表加载失败' });
          });
      })
      .finally(() => {
        this.setData({ classesLoading: false });
      });
  },

  onClassChange(e) {
    const index = Number(e.detail.value);
    const item = this.data.classOptions[index];
    if (!item) {
      wx.showToast({ title: '暂无可选项，可手动输入', icon: 'none' });
      return;
    }
    this.setData({
      classIndex: index,
      className: item.value,
      result: null,
      errorMsg: '',
    });
  },

  onClassInput(e) {
    this.setData({
      className: e.detail.value,
      result: null,
      errorMsg: '',
    });
  },

  onClassPickerTap() {
    const status = options.getOptionStatus('classes');
    if (status.loading) {
      wx.showToast({ title: '正在加载选项，请稍候', icon: 'none' });
      return;
    }
    if (status.error && !this.data.classOptions.length) {
      wx.showToast({ title: '选项加载失败，可手动输入', icon: 'none' });
      return;
    }
    if (!this.data.classOptions.length) {
      wx.showToast({ title: '暂无可选项，可手动输入', icon: 'none' });
    }
  },

  onTermInput(e) {
    this.setData({ term: e.detail.value, errorMsg: '' });
  },

  onGenerate() {
    const { className, term } = this.data;

    if (!className.trim()) {
      this.setData({ errorMsg: '请输入或选择班级' });
      return;
    }

    this.setData({ loading: true, result: null, errorMsg: '' });

    post('/api/ai/class-overview', {
      class_name: className.trim(),
      term: term || undefined,
    })
      .then((data) => {
        this.setData({ result: data });
        wx.showToast({ title: '分析完成', icon: 'success' });
      })
      .catch((err) => {
        this.setData({ errorMsg: err.message || '分析失败，请重试' });
      })
      .finally(() => {
        this.setData({ loading: false });
      });
  },
});
