const { get, post } = require('../../utils/request');
const auth = require('../../utils/auth');
const perm = require('../../utils/permission');

Page({
  data: {
    loading: false,
    errorMsg: '',
    list: [],
    page: 1,
    pageSize: 20,
    totalPages: 0,
  },

  onShow() {
    if (!auth.isLoggedIn()) {
      wx.reLaunch({ url: '/pages/login/index' });
      return;
    }
    if (!perm.canAiHistory()) {
      wx.showToast({ title: '无权查看 AI 历史', icon: 'none' });
      wx.switchTab({ url: '/pages/home/index' });
      return;
    }
    this.loadData();
  },

  loadData() {
    if (this.data.loading) return;
    this.setData({ loading: true, errorMsg: '' });
    get('/api/ai/history', { page: this.data.page, page_size: this.data.pageSize })
      .then((data) => {
        this.setData({
          list: (data.list || []).map((item) => this.decorate(item)),
          totalPages: data.total_pages || 0,
        });
      })
      .catch((err) => this.setData({ errorMsg: err.message || 'AI 历史加载失败' }))
      .finally(() => this.setData({ loading: false }));
  },

  decorate(item) {
    const typeLabels = {
      student_advice: '学生学习建议',
      class_overview: '班级学情分析',
      exam_paper: '试卷考点分析',
      combined: '联合复习建议',
    };
    const result = item.result || {};
    const summary = result.summary || result.diagnosis_summary || result.recognized_summary ||
      result.overview || result.raw_text || '已生成结构化分析结果';
    return {
      ...item,
      typeText: typeLabels[item.analysis_type] || item.analysis_type,
      summaryText: typeof summary === 'string' ? summary : JSON.stringify(summary),
      feedbackRating: item.my_feedback && item.my_feedback.rating,
    };
  },

  onFeedback(e) {
    const id = e.currentTarget.dataset.id;
    const rating = e.currentTarget.dataset.rating;
    post(`/api/ai/history/${id}/feedback`, { rating })
      .then(() => {
        const list = this.data.list.map((item) => (
          item.analysis_id === id ? { ...item, feedbackRating: rating } : item
        ));
        this.setData({ list });
        wx.showToast({ title: '反馈已记录', icon: 'success' });
      });
  },

  onPrevPage() {
    if (this.data.page > 1) this.setData({ page: this.data.page - 1 }, () => this.loadData());
  },

  onNextPage() {
    if (this.data.page < this.data.totalPages) this.setData({ page: this.data.page + 1 }, () => this.loadData());
  },
});
