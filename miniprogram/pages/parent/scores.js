const { get, post } = require('../../utils/request');
const auth = require('../../utils/auth');
const perm = require('../../utils/permission');
const { formatScore } = require('../../utils/format');

Page({
  data: {
    studentId: '',
    student: null,
    exams: [],
    loading: false,
    errorText: '',
    infoMessage: '',
    matchedScoreCount: 0,
    signatureText: '',
    remark: '',
  },

  onLoad(query) {
    if (!auth.isLoggedIn()) {
      wx.reLaunch({ url: '/pages/login/index' });
      return;
    }
    if (!perm.isParent()) {
      wx.showToast({ title: '无权限访问家长端', icon: 'none' });
      wx.switchTab({ url: '/pages/home/index' });
      return;
    }
    this.setData({ studentId: query.student_id || '' });
    this.loadData();
  },

  loadData() {
    if (!this.data.studentId) {
      return;
    }
    this.setData({ loading: true, errorText: '', infoMessage: '' });
    get(`/api/parents/children/${this.data.studentId}/published-scores`)
      .then((data) => {
        const rawExams = Array.isArray(data.list)
          ? data.list
          : (Array.isArray(data.exams) ? data.exams : []);
        const exams = rawExams.map((exam) => {
          const settings = exam.settings || {};
          const summary = exam.summary || {};
          return {
          ...exam,
          settings,
          summary,
          totalFmt: settings.show_total ? formatScore(summary.total_score) : '',
          avgFmt: formatScore(summary.average_score),
          classAverageFmt: exam.class_average !== null && exam.class_average !== undefined ? formatScore(exam.class_average) : '',
          scores: (Array.isArray(exam.scores) ? exam.scores : []).map((score) => ({
            ...score,
            scoreFmt: formatScore(score.score),
          })),
        };
        });
        this.setData({
          student: data.student || null,
          exams,
          infoMessage: data.message || '',
          matchedScoreCount: data.matched_score_count || 0,
        });
      })
      .catch((err) => {
        console.error('[ParentScores] 加载失败:', err.message);
        this.setData({ errorText: err.message || '加载失败，请重试' });
      })
      .finally(() => {
        this.setData({ loading: false });
      });
  },

  onInput(e) {
    const field = e.currentTarget.dataset.field;
    this.setData({ [field]: e.detail.value });
  },

  onConfirm(e) {
    const publishId = e.currentTarget.dataset.id;
    const { studentId, signatureText, remark } = this.data;
    if (!signatureText.trim()) {
      wx.showToast({ title: '请输入家长姓名确认', icon: 'none' });
      return;
    }
    post(`/api/parents/confirmations/${publishId}/confirm`, {
      student_id: studentId,
      signature_text: signatureText.trim(),
      remark: remark.trim() || undefined,
    })
      .then(() => {
        wx.showToast({ title: '确认成功', icon: 'success' });
        this.setData({ signatureText: '', remark: '' });
        this.loadData();
      })
      .catch((err) => {
        console.error('[ParentScores] 确认失败:', err.message);
      });
  },
});
