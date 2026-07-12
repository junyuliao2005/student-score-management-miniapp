const { get, del } = require('../../utils/request');
const { formatScore, formatRank, formatEmpty } = require('../../utils/format');
const { LEVEL_TAG_CLASS } = require('../../utils/constants');
const perm = require('../../utils/permission');
const auth = require('../../utils/auth');
const options = require('../../utils/options');
const exportFile = require('../../utils/export_file');

Page({
  data: {
    list: [],
    page: 1,
    pageSize: 20,
    total: 0,
    totalPages: 0,
    loading: false,
    filters: {
      student_id: '',
      student_name: '',
      course_id: '',
      class_name: '',
      term: '',
      exam_batch: '',
    },
    perms: {},
    optionMap: {},
  },

  onShow() {
    if (!auth.isLoggedIn()) {
      wx.reLaunch({ url: '/pages/login/index' });
      return;
    }

    if (!perm.canReadAllScores()) {
      if (perm.canReadSelfScore()) {
        wx.showToast({ title: '请在我的成绩中查看个人成绩', icon: 'none' });
        wx.switchTab({ url: '/pages/score-my/index' });
        return;
      }

      wx.showToast({ title: '无权限访问成绩查询', icon: 'none' });
      wx.switchTab({ url: '/pages/home/index' });
      return;
    }

    this.setData({
      perms: {
        canCreateScore: perm.canCreateScore(),
        canUpdateScore: perm.canUpdateScore(),
      },
    });
    this.loadOptions();
    this.loadData();
  },

  onExportScores() {
    if (!this.data.filters.exam_batch) {
      wx.showToast({ title: '请先选择考试批次', icon: 'none' });
      return;
    }
    wx.showLoading({ title: '正在生成' });
    get('/api/reports/scores/export', this.data.filters)
      .then((data) => exportFile.openBase64File(data))
      .catch((err) => wx.showToast({ title: err.message || '导出失败', icon: 'none' }))
      .finally(() => wx.hideLoading());
  },

  loadOptions() {
    options.loadOptionMap(['students', 'student_names', 'course_ids', 'classes', 'terms', 'exam_batches'])
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

  onSearch() {
    this.setData({ page: 1 });
    this.loadData();
  },

  onReset() {
    this.setData({
      page: 1,
      filters: {
        student_id: '',
        student_name: '',
        course_id: '',
        class_name: '',
        term: '',
        exam_batch: '',
      },
    });
    this.loadData();
  },

  loadData() {
    this.setData({ loading: true });

    const params = {
      page: this.data.page,
      page_size: this.data.pageSize,
    };

    // 添加非空筛选条件
    const { filters } = this.data;
    Object.keys(filters).forEach((key) => {
      if (filters[key]) {
        params[key] = filters[key];
      }
    });

    get('/api/scores', params)
      .then((data) => {
        const list = (data.list || []).map((item) => ({
          ...item,
          totalScoreFmt: formatScore(item.total_score),
          avgScoreFmt: formatScore(item.avg_score),
          rankFmt: formatRank(item.rank_no),
          levelTagClass: LEVEL_TAG_CLASS[item.level_tag] || '',
        }));
        let lastStudentId = '';
        const groupedList = list.map((item) => {
          const isGroupStart = item.student_id !== lastStudentId;
          lastStudentId = item.student_id;
          return {
            ...item,
            isGroupStart,
          };
        });

        this.setData({
          list: groupedList,
          total: data.total || 0,
          totalPages: data.total_pages || 0,
        });
      })
      .catch((err) => {
        console.error('[ScoreList] 加载失败:', err.message);
      })
      .finally(() => {
        this.setData({ loading: false });
      });
  },

  onAdd() {
    wx.navigateTo({ url: '/pages/score-edit/index' });
  },

  onEdit(e) {
    const item = e.currentTarget.dataset.item;
    const params = `score_id=${item.score_id}&student_id=${item.student_id}&course_id=${item.course_id}&score=${item.score}&exam_date=${item.exam_date}&exam_batch=${item.exam_batch}`;
    wx.navigateTo({ url: `/pages/score-edit/index?${params}` });
  },

  onDelete(e) {
    const scoreId = e.currentTarget.dataset.id;
    const name = e.currentTarget.dataset.name || '';

    wx.showModal({
      title: '确认删除',
      content: `确定要删除 ${name} 的这条成绩记录吗？`,
      success: (res) => {
        if (res.confirm) {
          del(`/api/scores/${scoreId}`)
            .then(() => {
              wx.showToast({ title: '删除成功', icon: 'success' });
              this.loadData();
            })
            .catch((err) => {
              console.error('[ScoreList] 删除失败:', err.message);
            });
        }
      },
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

  onPullDownRefresh() {
    this.loadData();
    wx.stopPullDownRefresh();
  },
});
