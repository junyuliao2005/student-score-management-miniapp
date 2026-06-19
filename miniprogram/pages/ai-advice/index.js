const { post } = require('../../utils/request');
const auth = require('../../utils/auth');

Page({
  data: {
    studentId: '',
    term: '2025-2026-2',
    loading: false,
    result: null,
    errorMsg: '',
    canInputStudentId: false,
  },

  onShow() {
    const roles = auth.getRoles();
    const perms = auth.getPermissions();
    const canInput = perms.includes('ai:student_advice:all');
    const user = auth.getUser();

    this.setData({
      canInputStudentId: canInput,
      studentId: canInput ? '' : (user ? user.user_id : ''),
    });
  },

  onStudentIdInput(e) {
    this.setData({ studentId: e.detail.value, errorMsg: '' });
  },

  onTermInput(e) {
    this.setData({ term: e.detail.value, errorMsg: '' });
  },

  onGenerate() {
    const { studentId, term } = this.data;

    if (!studentId.trim()) {
      this.setData({ errorMsg: '请输入学号' });
      return;
    }

    this.setData({ loading: true, result: null, errorMsg: '' });

    post('/api/ai/student-advice', {
      student_id: studentId.trim(),
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
