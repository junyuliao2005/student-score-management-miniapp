const auth = require('../../utils/auth');
const perm = require('../../utils/permission');
const { ROLE_NAMES, LEVEL_TAG_CLASS } = require('../../utils/constants');

Page({
  data: {
    user: {},
    roleName: '',
    roleTagClass: '',
    perms: {},
  },

  onShow() {
    this.loadUserInfo();
  },

  loadUserInfo() {
    const user = auth.getUser();
    const roles = auth.getRoles();

    if (!user) {
      wx.reLaunch({ url: '/pages/login/index' });
      return;
    }

    const primaryRole = roles[0] || 'student';
    const roleName = ROLE_NAMES[primaryRole] || primaryRole;
    const roleTagClass = primaryRole === 'admin' ? 'tag-fail' :
      primaryRole === 'teacher' ? 'tag-good' :
        primaryRole === 'parent' ? 'tag-pass' : 'tag-medium';

    this.setData({
      user: user,
      roleName: roleName,
      roleTagClass: roleTagClass,
      perms: {
        canCreateScore: perm.canCreateScore(),
        canUpdateScore: perm.canUpdateScore(),
        canReadAllScores: perm.canUseScoreList(),
        canReadSelfScore: perm.canUseMyScores(),
        canReadStats: perm.canUseStats(),
        canReadWarnings: perm.canReadWarnings(),
        canManageUsers: perm.canManageUsers(),
        canManageCourses: perm.canManageCourses(),
        canManageConfigs: perm.canManageConfigs(),
        canReadLogs: perm.canReadLogs(),
        canAiAdvice: perm.canAiAdvice(),
        canAiClass: perm.canAiClass(),
        canAiExam: perm.canAiExam(),
        canAiHistory: perm.canAiHistory(),
        isParent: perm.isParent(),
        canManageExamPublish: perm.isTeacher() || perm.isAdmin(),
        canManageParentBindings: perm.isTeacher() || perm.isAdmin(),
      },
    });
  },

  goTo(e) {
    const url = e.currentTarget.dataset.url;
    if (url) {
      const tabPages = [
        '/pages/home/index',
        '/pages/score-list/index',
        '/pages/stats/index',
        '/pages/score-my/index',
      ];
      const path = url.split('?')[0];

      if (tabPages.includes(path)) {
        wx.switchTab({ url: path });
        return;
      }

      wx.navigateTo({ url: url });
    }
  },

  onLogout() {
    wx.showModal({
      title: '确认退出',
      content: '确定要退出登录吗？',
      success(res) {
        if (res.confirm) {
          auth.logout();
          wx.reLaunch({ url: '/pages/login/index' });
        }
      },
    });
  },
});
