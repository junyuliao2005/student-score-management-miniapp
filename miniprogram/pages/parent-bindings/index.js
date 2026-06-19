const { get, post, del } = require('../../utils/request');
const auth = require('../../utils/auth');
const perm = require('../../utils/permission');

Page({
  data: {
    list: [],
    loading: false,
    errorText: '',
    canManage: false,
    form: {
      parent_username: '',
      student_username: '',
      relation: '家长',
    },
  },

  onShow() {
    if (!auth.isLoggedIn()) {
      wx.reLaunch({ url: '/pages/login/index' });
      return;
    }
    if (!perm.isTeacher() && !perm.isAdmin()) {
      wx.switchTab({ url: '/pages/home/index' });
      return;
    }
    this.setData({ canManage: perm.isAdmin() });
    this.loadData();
  },

  loadData() {
    this.setData({ loading: true, errorText: '' });
    get('/api/parent-bindings', { status: 1 })
      .then((data) => {
        this.setData({ list: Array.isArray(data.list) ? data.list : [] });
      })
      .catch((err) => {
        console.error('[ParentBindings] 加载失败:', err.message);
        this.setData({ errorText: err.message || '加载失败，请重试' });
      })
      .finally(() => {
        this.setData({ loading: false });
      });
  },

  onInput(e) {
    const field = e.currentTarget.dataset.field;
    this.setData({ [`form.${field}`]: e.detail.value });
  },

  onCreate() {
    const { form } = this.data;
    if (!form.parent_username || !form.student_username) {
      wx.showToast({ title: '请输入家长和学生用户名', icon: 'none' });
      return;
    }
    post('/api/parent-bindings', form).then(() => {
      wx.showToast({ title: '绑定成功', icon: 'success' });
      this.setData({ form: { parent_username: '', student_username: '', relation: '家长' } });
      this.loadData();
    });
  },

  onDisable(e) {
    const id = e.currentTarget.dataset.id;
    del(`/api/parent-bindings/${id}`).then(() => {
      wx.showToast({ title: '已停用', icon: 'none' });
      this.loadData();
    });
  },
});
