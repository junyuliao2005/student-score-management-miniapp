const { post } = require('../../utils/request');
const auth = require('../../utils/auth');

Page({
  data: {
    username: '',
    password: '',
    loading: false,
    errors: {},
  },

  onLoad() {
    if (!wx.getStorageSync('privacy_notice_ack')) {
      this.showPrivacyNotice();
    }
  },

  onUsernameInput(e) {
    this.setData({
      username: e.detail.value,
      'errors.username': '',
    });
  },

  onPasswordInput(e) {
    this.setData({
      password: e.detail.value,
      'errors.password': '',
    });
  },

  fillAccount(e) {
    const { username, password } = e.currentTarget.dataset;
    this.setData({
      username: username,
      password: password,
      errors: {},
    });
  },

  showPrivacyNotice() {
    wx.showModal({
      title: '隐私说明',
      content: '本系统仅用于学生成绩管理、家校沟通和学情分析。学生仅可查看本人数据，家长仅可查看已绑定子女数据，教师和管理员按权限进行管理。系统不会在未授权情况下向无关用户展示学生成绩。',
      confirmText: '我知道了',
      showCancel: false,
      success() {
        wx.setStorageSync('privacy_notice_ack', true);
      },
    });
  },

  onLogin() {
    const { username, password } = this.data;
    const errors = {};

    if (!username.trim()) {
      errors.username = '请输入用户名';
    }
    if (!password) {
      errors.password = '请输入密码';
    }

    if (Object.keys(errors).length > 0) {
      this.setData({ errors: errors });
      return;
    }

    this.setData({ loading: true, errors: {} });

    post('/api/auth/login', {
      username: username.trim(),
      password: password,
    })
      .then((data) => {
        // 保存登录信息
        auth.saveLoginInfo(
          data.token,
          data.user,
          data.roles,
          data.permissions
        );

        wx.showToast({
          title: '登录成功',
          icon: 'success',
          duration: 1000,
        });

        // 根据角色跳转
        const roles = auth.normalizeArray(data.roles);
        setTimeout(() => {
          if (roles.includes('student')) {
            wx.switchTab({ url: '/pages/score-my/index' });
          } else if (roles.includes('parent')) {
            wx.navigateTo({ url: '/pages/parent/home' });
          } else if (roles.includes('admin')) {
            wx.switchTab({ url: '/pages/home/index' });
          } else {
            wx.switchTab({ url: '/pages/home/index' });
          }
        }, 500);
      })
      .catch((err) => {
        console.error('[Login] 失败:', err.message);
      })
      .finally(() => {
        this.setData({ loading: false });
      });
  },
});
