const { get } = require('../../utils/request');
const auth = require('../../utils/auth');
const perm = require('../../utils/permission');

Page({
  data: {
    user: {},
    children: [],
    loading: false,
    errorText: '',
  },

  onShow() {
    if (!auth.isLoggedIn()) {
      wx.reLaunch({ url: '/pages/login/index' });
      return;
    }
    if (!perm.isParent()) {
      wx.showToast({ title: '无权限访问家长端', icon: 'none' });
      wx.switchTab({ url: '/pages/home/index' });
      return;
    }
    this.setData({ user: auth.getUser() || {} });
    this.loadChildren();
  },

  loadChildren() {
    this.setData({ loading: true, errorText: '' });
    get('/api/parents/my-children')
      .then((data) => {
        this.setData({
          children: Array.isArray(data.children) ? data.children : [],
        });
      })
      .catch((err) => {
        console.error('[ParentHome] 加载失败:', err.message);
        this.setData({ errorText: err.message || '加载失败，请重试' });
      })
      .finally(() => {
        this.setData({ loading: false });
      });
  },

  onChildTap(e) {
    const id = e.currentTarget.dataset.id;
    if (id) {
      wx.navigateTo({ url: `/pages/parent/scores?student_id=${id}` });
    }
  },
});
