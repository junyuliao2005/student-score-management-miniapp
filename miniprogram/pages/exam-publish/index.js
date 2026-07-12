const { get, post, del } = require('../../utils/request');
const auth = require('../../utils/auth');
const perm = require('../../utils/permission');
const options = require('../../utils/options');

Page({
  data: {
    list: [],
    confirmations: [],
    confirmationSummary: null,
    selectedPublishId: '',
    loading: false,
    errorText: '',
    formExpanded: false,
    optionMap: {},
    gradeOptions: [
      { label: '全部年级', value: '' },
      { label: '初一', value: '初一' },
      { label: '初二', value: '初二' },
      { label: '初三', value: '初三' },
      { label: '高一', value: '高一' },
      { label: '高二', value: '高二' },
      { label: '高三', value: '高三' },
    ],
    form: {
      exam_name: '',
      term: '',
      exam_batch: '',
      grade_name: '',
      class_name: '',
      show_total: true,
      show_rank: true,
      show_grade_rank: true,
      show_class_average: true,
      show_subject_scores: true,
      require_parent_signature: true,
    },
  },

  onShow() {
    if (!auth.isLoggedIn()) {
      wx.reLaunch({ url: '/pages/login/index' });
      return;
    }
    if (!perm.isTeacher() && !perm.isAdmin()) {
      wx.showToast({ title: '无权限访问发布管理', icon: 'none' });
      wx.switchTab({ url: '/pages/home/index' });
      return;
    }
    this.loadOptions();
    this.loadList();
  },

  loadOptions() {
    options.loadOptionMap(['terms', 'exam_batches', 'classes']).then((optionMap) => {
      const classOptions = Array.isArray(optionMap.classes) ? optionMap.classes : [];
      this.setData({
        optionMap: {
          ...optionMap,
          classes: [{ label: '全部班级', value: '' }].concat(classOptions),
        },
      });
    }).catch((err) => {
      console.error('[ExamPublish] 选项加载失败:', err.message);
      this.setData({ optionMap: {} });
    });
  },

  loadList() {
    this.setData({ loading: true, errorText: '' });
    get('/api/exam-publish', { page: 1, page_size: 50 })
      .then((data) => {
        this.setData({ list: Array.isArray(data.list) ? data.list : [] });
      })
      .catch((err) => {
        console.error('[ExamPublish] 加载失败:', err.message);
        this.setData({ errorText: err.message || '加载失败，请重试' });
      })
      .finally(() => {
        this.setData({ loading: false });
      });
  },

  onToggleForm() {
    this.setData({ formExpanded: !this.data.formExpanded });
  },

  onInput(e) {
    const field = e.currentTarget.dataset.field;
    this.setData({ [`form.${field}`]: e.detail.value });
  },

  onSwitch(e) {
    const field = e.currentTarget.dataset.field;
    this.setData({ [`form.${field}`]: e.detail.value });
  },

  onPick(e) {
    const { type, field } = e.currentTarget.dataset;
    const index = Number(e.detail.value);
    const source = type === 'grades' ? this.data.gradeOptions : this.data.optionMap[type];
    const optionList = Array.isArray(source) ? source : [];
    const item = optionList[index];
    if (item) {
      this.setData({ [`form.${field}`]: item.value });
    }
  },

  onCreate() {
    const form = {
      ...this.data.form,
      grade_name: this.normalizeScopeValue(this.data.form.grade_name),
      class_name: this.normalizeScopeValue(this.data.form.class_name),
    };
    if (!form.exam_name || !form.term || !form.exam_batch) {
      wx.showToast({ title: '请填写考试名称、学期、批次', icon: 'none' });
      return;
    }
    post('/api/exam-publish', form).then(() => {
      wx.showToast({ title: '创建成功', icon: 'success' });
      this.setData({ formExpanded: false });
      this.loadList();
    });
  },

  onPublish(e) {
    const id = e.currentTarget.dataset.id;
    post(`/api/exam-publish/${id}/publish`).then(() => {
      wx.showToast({ title: '已发布', icon: 'success' });
      this.loadList();
    });
  },

  onWithdraw(e) {
    const id = e.currentTarget.dataset.id;
    post(`/api/exam-publish/${id}/withdraw`).then(() => {
      wx.showToast({ title: '已撤回', icon: 'success' });
      this.loadList();
    });
  },

  onDelete(e) {
    const id = e.currentTarget.dataset.id;
    wx.showModal({
      title: '确认删除',
      content: '确认删除该发布记录吗？不会删除原始成绩。',
      success: (res) => {
        if (!res.confirm) {
          return;
        }
        del(`/api/exam-publish/${id}`).then(() => {
          wx.showToast({ title: '已删除', icon: 'success' });
          this.loadList();
        });
      },
    });
  },

  onLoadConfirmations(e) {
    const id = e.currentTarget.dataset.id;
    get(`/api/exam-publish/${id}/confirmations`).then((data) => {
      this.setData({
        selectedPublishId: id,
        confirmations: Array.isArray(data.list) ? data.list : [],
        confirmationSummary: {
          confirmed: data.confirmed_count || 0,
          pending: data.pending_count || 0,
        },
      });
    }).catch((err) => {
      console.error('[ExamPublish] 加载确认情况失败:', err.message);
      this.setData({ selectedPublishId: id, confirmations: [], confirmationSummary: null });
    });
  },

  onExportConfirmations() {
    const id = this.data.selectedPublishId;
    if (!id) return;
    get(`/api/exam-publish/${id}/confirmations/export`)
      .then((data) => {
        const filePath = `${wx.env.USER_DATA_PATH}/${data.filename || `parent-confirmations-${id}.xlsx`}`;
        wx.getFileSystemManager().writeFile({
          filePath,
          data: data.content_base64,
          encoding: 'base64',
          success: () => wx.openDocument({ filePath, fileType: 'xlsx', showMenu: true }),
          fail: () => wx.showToast({ title: '导出文件保存失败', icon: 'none' }),
        });
      });
  },

  normalizeScopeValue(value) {
    const text = String(value || '').trim();
    if (!text || text === '全部' || text === '全部年级' || text === '全部班级') {
      return '';
    }
    return text;
  },
});
