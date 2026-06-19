const { get, post } = require('../../utils/request');
const { formatScore, formatPercent } = require('../../utils/format');
const { LEVEL_TAG_CLASS } = require('../../utils/constants');
const perm = require('../../utils/permission');
const auth = require('../../utils/auth');
const options = require('../../utils/options');

Page({
  data: {
    overview: null,
    rankings: [],
    totalRankings: [],
    subjectRankings: [],
    honorRoll: null,
    activeTab: 'overview',
    rankPage: 1,
    rankPageSize: 20,
    rankTotalPages: 0,
    subjectPage: 1,
    subjectTotalPages: 0,
    loading: false,
    refreshing: false,
    filters: {
      term: '2025-2026-2',
      class_name: '',
      exam_batch: '',
      course_id: '',
    },
    perms: {},
    optionMap: {},
  },

  onShow() {
    if (!auth.isLoggedIn()) {
      wx.reLaunch({ url: '/pages/login/index' });
      return;
    }

    if (!perm.canReadStats()) {
      wx.showToast({ title: '暂无统计分析权限', icon: 'none' });
      if (perm.canReadSelfScore()) {
        wx.switchTab({ url: '/pages/score-my/index' });
      } else {
        wx.switchTab({ url: '/pages/home/index' });
      }
      return;
    }

    this.setData({
      perms: {
        canRefreshStats: perm.canRefreshStats(),
      },
    });
    this.loadOptions();
    this.loadData();
  },

  loadOptions() {
    options.loadOptionMap(['classes', 'exam_batches', 'courses'])
      .then((optionMap) => {
        this.setData({ optionMap });
      });
  },

  onTabChange(e) {
    const tab = e.currentTarget.dataset.tab;
    if (!tab || tab === this.data.activeTab) {
      return;
    }
    this.setData({
      activeTab: tab,
      rankPage: 1,
      subjectPage: 1,
    });
    this.loadData(true);
  },

  onFilterInput(e) {
    const field = e.currentTarget.dataset.field;
    this.setData({ [`filters.${field}`]: e.detail.value });
  },

  onPickFilter(e) {
    const { type, field } = e.currentTarget.dataset;
    const index = Number(e.detail.value);
    const list = this.data.optionMap[type] || [];
    if (!list.length) {
      wx.showToast({ title: '暂无可选项，可手动输入', icon: 'none' });
      return;
    }
    const item = list[index];
    if (item) {
      this.setData({ [`filters.${field}`]: item.value });
    }
  },

  onPickerTap(e) {
    const type = e.currentTarget.dataset.type;
    const list = this.data.optionMap[type] || [];
    const status = options.getOptionStatus(type);
    if (status.loading) {
      wx.showToast({ title: '正在加载选项，请稍候', icon: 'none' });
      return;
    }
    if (status.error && !list.length) {
      wx.showToast({ title: '选项加载失败，可手动输入', icon: 'none' });
      return;
    }
    if (!list.length) {
      wx.showToast({ title: '暂无可选项，可手动输入', icon: 'none' });
    }
  },

  onSearch() {
    if (this.data.loading) {
      return;
    }
    this.setData({ rankPage: 1, subjectPage: 1 });
    this.loadData(true);
  },

  loadData(showBatchTip = false) {
    if (this.data.loading) {
      return;
    }
    this.setData({ loading: true });

    const { activeTab, filters, rankPage, rankPageSize, subjectPage } = this.data;
    const params = {};
    Object.keys(filters).forEach((key) => {
      if (filters[key]) {
        params[key] = filters[key];
      }
    });
    if (activeTab !== 'subject') {
      delete params.course_id;
    }

    const requireBatch = ['total', 'subject', 'honor'].includes(activeTab);
    if (requireBatch && !params.exam_batch) {
      this.clearActiveTabData(activeTab);
      if (showBatchTip) {
        wx.showToast({ title: '请先选择考试批次', icon: 'none' });
      }
      this.setData({ loading: false });
      return;
    }
    if (activeTab === 'subject' && !params.course_id) {
      this.clearActiveTabData(activeTab);
      if (showBatchTip) {
        wx.showToast({ title: '请先选择课程', icon: 'none' });
      }
      this.setData({ loading: false });
      return;
    }

    let task;
    if (activeTab === 'total') {
      task = get('/api/stats/total-rankings', { ...params, page: rankPage, page_size: rankPageSize })
        .then((data) => this.applyTotalRankings(data));
    } else if (activeTab === 'subject') {
      task = get('/api/stats/subject-rankings', { ...params, page: subjectPage, page_size: rankPageSize })
        .then((data) => this.applySubjectRankings(data));
    } else if (activeTab === 'honor') {
      task = get('/api/stats/honor-roll', params)
        .then((data) => this.applyHonorRoll(data));
    } else {
      task = get('/api/stats/overview', params)
        .then((data) => this.applyOverview(data));
    }

    task
      .catch((err) => {
        console.error('[Stats] 加载失败:', err.message);
      })
      .finally(() => {
        this.setData({ loading: false });
      });
  },

  clearActiveTabData(tab) {
    if (tab === 'total') {
      this.setData({ totalRankings: [], rankTotalPages: 0 });
    } else if (tab === 'subject') {
      this.setData({ subjectRankings: [], subjectTotalPages: 0 });
    } else if (tab === 'honor') {
      this.setData({ honorRoll: null });
    }
  },

  applyOverview(data) {
    if (!data) {
      this.setData({ overview: null });
      return;
    }
    this.setData({
      overview: {
        student_count: data.student_count || 0,
        score_count: data.score_count || 0,
        avg_score_fmt: formatScore(data.avg_score),
        max_score_fmt: formatScore(data.max_score),
        min_score_fmt: formatScore(data.min_score),
        excellent_rate_fmt: formatPercent(data.excellent_rate),
        pass_rate_fmt: formatPercent(data.pass_rate),
        low_score_count: data.low_score_count || 0,
      },
    });
  },

  applyTotalRankings(data) {
    const totalRankings = (data.list || []).map((item) => ({
      ...item,
      rankNo: item.overall_rank || '-',
      totalScoreFmt: formatScore(item.total_score),
      avgScoreFmt: formatScore(item.average_score),
      subjectText: (Array.isArray(item.subjects) ? item.subjects : []).map((subject) => (
        `${subject.course_name || subject.course_id} ${formatScore(subject.score)}`
      )).join('；'),
    }));
    this.setData({
      totalRankings,
      rankTotalPages: data.total_pages || 0,
    });
  },

  applySubjectRankings(data) {
    const subjectRankings = (data.list || []).map((item) => ({
      ...item,
      scoreFmt: formatScore(item.score),
    }));
    this.setData({
      subjectRankings,
      subjectTotalPages: data.total_pages || 0,
    });
  },

  applyHonorRoll(data) {
    this.setData({
      honorRoll: {
        topTotal: (data.top_total || []).map((item) => ({
          ...item,
          totalScoreFmt: formatScore(item.total_score),
          avgScoreFmt: formatScore(item.average_score),
        })),
        subjectBest: (data.subject_best || []).map((item) => ({
          ...item,
          scoreFmt: formatScore(item.score),
        })),
        excellentStudents: (data.excellent_students || []).map((item) => ({
          ...item,
          totalScoreFmt: formatScore(item.total_score),
          avgScoreFmt: formatScore(item.average_score),
        })),
      },
    });
  },

  onRefresh() {
    if (this.data.refreshing) {
      return;
    }
    const { filters } = this.data;
    this.setData({ refreshing: true });

    post('/api/stats/evaluate', {
      term: filters.term || undefined,
      class_name: filters.class_name || undefined,
    })
      .then((data) => {
        wx.showToast({
          title: '统计刷新完成',
          icon: 'success',
          duration: 2000,
        });
        this.loadData();
      })
      .catch((err) => {
        console.error('[Stats] 刷新失败:', err.message);
      })
      .finally(() => {
        this.setData({ refreshing: false });
      });
  },

  onPrevRankPage() {
    if (this.data.loading) {
      return;
    }
    if (this.data.activeTab === 'subject') {
      if (this.data.subjectPage > 1) {
        this.setData({ subjectPage: this.data.subjectPage - 1 });
        this.loadData(true);
      }
      return;
    }
    if (this.data.activeTab === 'total' && this.data.rankPage > 1) {
      this.setData({ rankPage: this.data.rankPage - 1 });
      this.loadData();
    }
  },

  onNextRankPage() {
    if (this.data.loading) {
      return;
    }
    if (this.data.activeTab === 'subject') {
      if (this.data.subjectPage < this.data.subjectTotalPages) {
        this.setData({ subjectPage: this.data.subjectPage + 1 });
        this.loadData(true);
      }
      return;
    }
    if (this.data.activeTab === 'total' && this.data.rankPage < this.data.rankTotalPages) {
      this.setData({ rankPage: this.data.rankPage + 1 });
      this.loadData();
    }
  },
});
