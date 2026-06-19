const { get, post } = require('../../utils/request');
const { formatScore } = require('../../utils/format');
const { WARNING_TYPE_NAMES, WARNING_TAG_CLASS } = require('../../utils/constants');
const perm = require('../../utils/permission');
const options = require('../../utils/options');

Page({
  data: {
    warnings: [],
    page: 1,
    pageSize: 20,
    total: 0,
    totalPages: 0,
    loading: false,
    refreshing: false,
    filters: {
      term: '2025-2026-2',
      class_name: '',
      warning_type: '',
    },
    warningTypeOptions: ['全部类型', '低分预警', '偏科预警'],
    warningTypeIndex: 0,
    perms: {},
    optionMap: {},
  },

  onShow() {
    this.setData({
      perms: {
        canRefreshWarnings: perm.canRefreshWarnings(),
      },
    });
    this.loadOptions();
    this.loadData();
  },

  loadOptions() {
    options.loadOptionMap(['classes'])
      .then((optionMap) => {
        this.setData({ optionMap });
      });
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

  onWarningTypeChange(e) {
    const index = parseInt(e.detail.value);
    const typeMap = { 0: '', 1: 'low_score', 2: 'subject_bias' };
    this.setData({
      warningTypeIndex: index,
      'filters.warning_type': typeMap[index],
    });
  },

  onSearch() {
    this.setData({ page: 1 });
    this.loadData();
  },

  loadData() {
    this.setData({ loading: true });

    const params = {
      page: this.data.page,
      page_size: this.data.pageSize,
    };
    const { filters } = this.data;
    Object.keys(filters).forEach((key) => {
      if (filters[key]) {
        params[key] = filters[key];
      }
    });

    get('/api/warnings', params)
      .then((data) => {
        const warnings = (data.list || []).map((item) => ({
          ...item,
          warningTypeName: WARNING_TYPE_NAMES[item.warning_type] || item.warning_type,
          warningTagClass: WARNING_TAG_CLASS[item.warning_type] || '',
          avgScoreFmt: formatScore(item.avg_score),
          reason: this.formatWarningReason(item),
          maxSubjectText: item.max_subject || item.max_course_name || item.max_course_id || '未知科目',
          minSubjectText: item.min_subject || item.min_course_name || item.min_course_id || '未知科目',
          maxScoreText: this.safeValue(item.max_score),
          minScoreText: this.safeValue(item.min_score),
          biasText: this.safeValue(item.bias),
          courseText: item.course_name || item.course_id || item.subject || '未知科目',
        }));

        this.setData({
          warnings: warnings,
          total: data.total || 0,
          totalPages: data.total_pages || 0,
        });
      })
      .catch((err) => {
        console.error('[Warnings] 加载失败:', err.message);
      })
      .finally(() => {
        this.setData({ loading: false });
      });
  },

  safeValue(value, fallback = '-') {
    if (value === undefined || value === null || value === '' || Number.isNaN(value)) {
      return fallback;
    }
    return value;
  },

  formatWarningReason(item) {
    const backendReason = item.reason || item.warning_reason;
    if (backendReason && !String(backendReason).includes('undefined')) {
      return backendReason;
    }

    if (item.warning_type === 'low_score') {
      const courseName = item.course_name || item.course_id || item.subject || '未知科目';
      const score = this.safeValue(item.score);
      return `${courseName} 成绩 ${score} 低于预警线`;
    }

    if (item.warning_type === 'subject_bias') {
      const maxSubject = item.max_subject || item.max_course_name || item.max_course_id || '未知科目';
      const minSubject = item.min_subject || item.min_course_name || item.min_course_id || '未知科目';
      const maxScore = this.safeValue(item.max_score);
      const minScore = this.safeValue(item.min_score);
      const bias = this.safeValue(item.bias);
      return `最高 ${maxSubject}(${maxScore}) - 最低 ${minSubject}(${minScore}) = ${bias}`;
    }

    return '暂无原因';
  },

  onRefresh() {
    const { filters } = this.data;
    this.setData({ refreshing: true });

    post('/api/warnings/refresh', {
      term: filters.term || undefined,
      class_name: filters.class_name || undefined,
    })
      .then(() => {
        wx.showToast({
          title: '预警刷新完成',
          icon: 'success',
          duration: 2000,
        });
        this.loadData();
      })
      .catch((err) => {
        console.error('[Warnings] 刷新失败:', err.message);
      })
      .finally(() => {
        this.setData({ refreshing: false });
      });
  },

  onPrevPage() {
    if (this.data.page > 1) {
      this.setData({ page: this.data.page - 1 });
      this.loadData();
    }
  },

  onNextPage() {
    if (this.data.page < this.data.totalPages) {
      this.setData({ page: this.data.page + 1 });
      this.loadData();
    }
  },
});
