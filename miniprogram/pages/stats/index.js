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
    trendSeries: [],
    distribution: null,
    progressRankings: [],
    biasItems: [],
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
      baseline_batch: '',
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
    if (!['subject', 'distribution', 'trend'].includes(activeTab)) {
      delete params.course_id;
    }
    if (activeTab !== 'progress') {
      delete params.baseline_batch;
    }

    const requireBatch = ['total', 'subject', 'honor', 'distribution', 'bias'].includes(activeTab);
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
    if (activeTab === 'progress' && (!params.term || !params.baseline_batch || !params.exam_batch)) {
      this.clearActiveTabData(activeTab);
      if (showBatchTip) wx.showToast({ title: '请选择学期、基准批次和当前批次', icon: 'none' });
      this.setData({ loading: false });
      return;
    }
    if (activeTab === 'trend' && !params.class_name) {
      this.clearActiveTabData(activeTab);
      if (showBatchTip) wx.showToast({ title: '请先选择班级', icon: 'none' });
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
    } else if (activeTab === 'trend') {
      task = get('/api/stats/trends', params).then((data) => this.applyTrend(data));
    } else if (activeTab === 'distribution') {
      task = get('/api/stats/distribution', params).then((data) => this.applyDistribution(data));
    } else if (activeTab === 'progress') {
      task = get('/api/stats/progress-rankings', {
        term: params.term,
        class_name: params.class_name,
        baseline_batch: params.baseline_batch,
        current_batch: params.exam_batch,
        page: rankPage,
        page_size: rankPageSize,
      }).then((data) => this.applyProgress(data));
    } else if (activeTab === 'bias') {
      task = get('/api/stats/bias-analysis', {
        term: params.term,
        class_name: params.class_name,
        exam_batch: params.exam_batch,
        page: rankPage,
        page_size: rankPageSize,
      }).then((data) => this.applyBias(data));
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
    } else if (tab === 'trend') {
      this.setData({ trendSeries: [] });
    } else if (tab === 'distribution') {
      this.setData({ distribution: null });
    } else if (tab === 'progress') {
      this.setData({ progressRankings: [], rankTotalPages: 0 });
    } else if (tab === 'bias') {
      this.setData({ biasItems: [], rankTotalPages: 0 });
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

  applyTrend(data) {
    const values = Array.isArray(data.series) ? data.series : [];
    this.setData({
      trendSeries: values.map((item) => ({
        ...item,
        scoreFmt: formatScore(item.average_score),
        width: Math.max(4, Math.min(100, Number(item.average_score) || 0)),
      })),
    });
  },

  applyDistribution(data) {
    const segments = Array.isArray(data.segments) ? data.segments : [];
    const maxCount = Math.max(1, ...segments.map((item) => Number(item.count) || 0));
    this.setData({
      distribution: {
        total: data.total || 0,
        segments: segments.map((item) => ({
          ...item,
          rateFmt: formatPercent(item.rate),
          width: Math.round(((Number(item.count) || 0) / maxCount) * 100),
        })),
      },
    });
  },

  applyProgress(data) {
    this.setData({
      progressRankings: (data.list || []).map((item) => ({
        ...item,
        baselineFmt: formatScore(item.baseline_score),
        currentFmt: formatScore(item.current_score),
        deltaFmt: `${Number(item.delta) >= 0 ? '+' : ''}${formatScore(item.delta)}`,
      })),
      rankTotalPages: data.total_pages || 0,
    });
  },

  applyBias(data) {
    this.setData({
      biasItems: (data.list || []).map((item) => ({
        ...item,
        highestText: `${item.highest_subject.course_name || item.highest_subject.course_id} ${formatScore(item.highest_subject.score)}`,
        lowestText: `${item.lowest_subject.course_name || item.lowest_subject.course_id} ${formatScore(item.lowest_subject.score)}`,
        gapFmt: formatScore(item.gap),
      })),
      rankTotalPages: data.total_pages || 0,
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
    if (['total', 'progress', 'bias'].includes(this.data.activeTab) && this.data.rankPage > 1) {
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
    if (['total', 'progress', 'bias'].includes(this.data.activeTab) && this.data.rankPage < this.data.rankTotalPages) {
      this.setData({ rankPage: this.data.rankPage + 1 });
      this.loadData();
    }
  },
});
