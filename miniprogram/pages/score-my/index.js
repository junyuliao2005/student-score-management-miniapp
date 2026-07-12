const { get } = require('../../utils/request');
const { formatScore, formatRank } = require('../../utils/format');
const { LEVEL_TAG_CLASS } = require('../../utils/constants');
const perm = require('../../utils/permission');
const auth = require('../../utils/auth');
const options = require('../../utils/options');
const exportFile = require('../../utils/export_file');

Page({
  data: {
    studentInfo: null,
    scores: [],
    summary: null,
    displaySettings: {
      show_total: true,
      show_rank: true,
      show_class_stats: true,
      show_warning: true,
    },
    loading: false,
    emptyText: '暂无成绩数据',
    trendLoading: false,
    trendSeries: [],
    showTrend: false,
    filterExpanded: false,
    filters: {
      term: '',
      course_id: '',
      course_name: '',
      exam_batch: '',
    },
    optionMap: {
      terms: [],
      exam_batches: [],
      course_ids: [],
      course_names: [],
    },
  },

  onShow() {
    if (!auth.isLoggedIn()) {
      wx.reLaunch({ url: '/pages/login/index' });
      return;
    }

    if (perm.isAdmin() || perm.isTeacher()) {
      wx.showToast({ title: '请使用成绩查询查看学生成绩', icon: 'none' });
      wx.switchTab({ url: '/pages/score-list/index' });
      return;
    }

    if (!perm.isStudent() || !perm.canReadSelfScore()) {
      wx.showToast({ title: '无权限查看我的成绩', icon: 'none' });
      wx.switchTab({ url: '/pages/home/index' });
      return;
    }

    this.loadOptions(true);
  },

  loadOptions(autoLoad = false) {
    get('/api/scores/my/options', {}, { showError: false })
      .then((data) => {
        const optionMap = this.normalizeMyOptions(data);
        const nextFilters = { ...this.data.filters };
        if (!nextFilters.term && optionMap.terms.length) {
          nextFilters.term = optionMap.terms[optionMap.terms.length - 1].value;
        }
        if (!nextFilters.exam_batch && optionMap.exam_batches.length) {
          nextFilters.exam_batch = optionMap.exam_batches[optionMap.exam_batches.length - 1].value;
        }
        this.setData({
          optionMap: this.mergeOptionMap(this.data.optionMap, optionMap),
          filters: nextFilters,
        });
        if (autoLoad) {
          this.loadData();
        }
      })
      .catch(() => {
        options.loadOptionMap(['terms', 'courses', 'exam_batches']).then((optionMap) => {
          this.setData({
            optionMap: this.mergeOptionMap(this.data.optionMap, this.normalizeMyOptions(optionMap)),
          });
          if (autoLoad) {
            this.loadData();
          }
        }).catch(() => {
          if (autoLoad) {
            this.loadData();
          }
        });
      });
  },

  onToggleFilter() {
    this.setData({ filterExpanded: !this.data.filterExpanded });
  },

  onExportPdf() {
    const studentId = this.data.studentInfo && this.data.studentInfo.student_id;
    if (!studentId) {
      wx.showToast({ title: '暂无可导出成绩', icon: 'none' });
      return;
    }
    wx.showLoading({ title: '正在生成' });
    get(`/api/reports/students/${encodeURIComponent(studentId)}/scores.pdf`, {
      term: this.data.filters.term || undefined,
      exam_batch: this.data.filters.exam_batch || undefined,
    })
      .then((data) => exportFile.openBase64File(data))
      .catch((err) => wx.showToast({ title: err.message || '报告生成失败', icon: 'none' }))
      .finally(() => wx.hideLoading());
  },

  onLoadTrend() {
    if (this.data.trendLoading) return;
    if (this.data.showTrend) {
      this.setData({ showTrend: false });
      return;
    }
    this.setData({ trendLoading: true });
    get('/api/stats/my-trend', {
      term: this.data.filters.term || undefined,
      course_id: this.data.filters.course_id || undefined,
    })
      .then((data) => {
        this.setData({
          trendSeries: (data.series || []).map((item) => ({
            ...item,
            scoreFmt: formatScore(item.average_score),
            width: Math.max(4, Math.min(100, Number(item.average_score) || 0)),
          })),
          showTrend: true,
        });
      })
      .finally(() => this.setData({ trendLoading: false }));
  },

  onFilterInput(e) {
    const field = e.currentTarget.dataset.field;
    const nextData = { [`filters.${field}`]: e.detail.value };
    if (field === 'course_id') {
      nextData['filters.course_name'] = '';
    }
    if (field === 'course_name') {
      nextData['filters.course_id'] = '';
    }
    this.setData(nextData);
  },

  onPickFilter(e) {
    const { type, field } = e.currentTarget.dataset;
    const index = Number(e.detail.value);
    const list = Array.isArray(this.data.optionMap[type]) ? this.data.optionMap[type] : [];
    if (!list.length) {
      wx.showToast({ title: '暂无可选项，可手动输入', icon: 'none' });
      return;
    }
    const item = list[index];
    if (item) {
      const nextData = { [`filters.${field}`]: item.value };
      if (field === 'course_id') {
        nextData['filters.course_name'] = '';
      }
      if (field === 'course_name') {
        nextData['filters.course_id'] = '';
      }
      this.setData(nextData);
    }
  },

  onPickerTap(e) {
    const type = e.currentTarget.dataset.type;
    const list = Array.isArray(this.data.optionMap[type]) ? this.data.optionMap[type] : [];
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
    this.setData({ filterExpanded: false });
    this.loadData();
  },

  onReset() {
    this.setData({
      filters: { term: '', course_id: '', course_name: '', exam_batch: '' },
    });
    this.loadData();
  },

  loadData() {
    this.setData({ loading: true });

    const params = {};
    const { filters } = this.data;
    Object.keys(filters).forEach((key) => {
      if (key === 'course_name') {
        return;
      }
      if (filters[key]) {
        params[key] = filters[key];
      }
    });
    if (!params.course_id && filters.course_name) {
      params.course_id = filters.course_name;
    }

    get('/api/scores/my', params)
      .then((data) => {
        const scores = (Array.isArray(data.scores) ? data.scores : []).map((item) => ({
          ...item,
          courseNameText: item.course_name || item.course_id || '未知科目',
          totalScoreFmt: formatScore(item.total_score),
          avgScoreFmt: formatScore(item.avg_score),
          rankFmt: formatRank(item.rank_no),
          levelTagClass: LEVEL_TAG_CLASS[item.level_tag] || '',
        }));
        const scoreOptionMap = this.buildOptionsFromScores(scores, data.summary);

        this.setData({
          studentInfo: {
            student_id: data.student_id,
            student_name: data.student_name,
            class_name: data.class_name,
          },
          scores: scores,
          emptyText: this.getEmptyText(),
          summary: data.summary ? {
            ...data.summary,
            totalScoreFmt: formatScore(data.summary.total_score),
            avgScoreFmt: formatScore(data.summary.average_score),
            classRankFmt: formatRank(data.summary.class_rank),
            overallRankFmt: formatRank(data.summary.overall_rank),
            subjectCountText: data.summary.subject_count || 0,
            subjectText: (Array.isArray(data.summary.subjects) ? data.summary.subjects : []).map((subject) => (
              `${subject.course_name || subject.course_id || '未知科目'} ${formatScore(subject.score)}`
            )).join('；'),
          } : null,
          displaySettings: data.display_settings || this.data.displaySettings,
          optionMap: this.mergeOptionMap(this.data.optionMap, scoreOptionMap),
        });
      })
      .catch((err) => {
        console.error('[ScoreMy] 加载失败:', err.message);
      })
      .finally(() => {
        this.setData({ loading: false });
      });
  },

  getEmptyText() {
    const { term, exam_batch, course_id, course_name } = this.data.filters;
    if (term || exam_batch || course_id || course_name) {
      if (term && exam_batch && !course_id && !course_name) {
        return '暂无该考试批次成绩';
      }
      return '暂无匹配成绩，可尝试不填课程号查询全部科目';
    }
    return '暂无成绩数据';
  },

  normalizeMyOptions(data = {}) {
    const courses = Array.isArray(data.courses) ? data.courses : [];
    return {
      terms: this.normalizeOptionList(data.terms),
      exam_batches: this.normalizeOptionList(data.exam_batches),
      course_ids: this.normalizeCourseIdOptions(courses),
      course_names: this.normalizeCourseNameOptions(courses),
    };
  },

  normalizeOptionList(list) {
    if (!Array.isArray(list)) {
      return [];
    }
    return list
      .map((item) => {
        if (typeof item === 'string') {
          const text = item.trim();
          return text ? { label: text, value: text } : null;
        }
        const value = String((item && (item.value || item.label)) || '').trim();
        const label = String((item && (item.label || item.value)) || '').trim();
        return value ? { label: label || value, value } : null;
      })
      .filter(Boolean);
  },

  normalizeCourseIdOptions(courses) {
    return this.normalizeOptionList(courses).map((item) => ({
      label: this.formatCourseIdLabel(item.value, item.label),
      value: item.value,
    }));
  },

  normalizeCourseNameOptions(courses) {
    return this.normalizeOptionList(courses)
      .map((item) => {
        const name = this.extractCourseName(item.label, item.value);
        return name ? { label: name, value: name } : null;
      })
      .filter(Boolean);
  },

  buildOptionsFromScores(scores, summary) {
    const rows = Array.isArray(scores) ? scores : [];
    const summarySubjects = summary && Array.isArray(summary.subjects) ? summary.subjects : [];
    const courseRows = rows.concat(summarySubjects);
    return {
      terms: rows
        .filter((item) => item.term)
        .map((item) => ({ label: item.term, value: item.term })),
      exam_batches: rows
        .filter((item) => item.exam_batch)
        .map((item) => ({ label: item.exam_batch, value: item.exam_batch })),
      course_ids: courseRows
        .filter((item) => item.course_id)
        .map((item) => ({
          label: this.formatCourseIdLabel(item.course_id, item.course_name),
          value: item.course_id,
        })),
      course_names: courseRows
        .filter((item) => item.course_name)
        .map((item) => ({ label: item.course_name, value: item.course_name })),
    };
  },

  mergeOptionMap(base = {}, extra = {}) {
    return {
      terms: this.mergeOptions(base.terms, extra.terms),
      exam_batches: this.mergeOptions(base.exam_batches, extra.exam_batches),
      course_ids: this.mergeOptions(base.course_ids, extra.course_ids),
      course_names: this.mergeOptions(base.course_names, extra.course_names),
    };
  },

  mergeOptions(a, b) {
    const result = [];
    const seen = {};
    this.normalizeOptionList(a).concat(this.normalizeOptionList(b)).forEach((item) => {
      if (!item.value || seen[item.value]) {
        return;
      }
      seen[item.value] = true;
      result.push(item);
    });
    return result;
  },

  formatCourseIdLabel(courseId, courseNameOrLabel) {
    const id = String(courseId || '').trim();
    const name = this.extractCourseName(courseNameOrLabel, id);
    return name && name !== id ? `${id} ${name}` : id;
  },

  extractCourseName(label, value) {
    const text = String(label || '').trim();
    const val = String(value || '').trim();
    if (!text) {
      return '';
    }
    const parenMatch = text.match(/^(.+)[（(][^)）]+[)）]$/);
    if (parenMatch) {
      return parenMatch[1].trim();
    }
    const spaceParts = text.split(/\s+/);
    if (spaceParts.length > 1 && spaceParts[0] === val) {
      return spaceParts.slice(1).join(' ').trim();
    }
    return text === val ? '' : text;
  },

  onPullDownRefresh() {
    this.loadData();
    wx.stopPullDownRefresh();
  },
});
