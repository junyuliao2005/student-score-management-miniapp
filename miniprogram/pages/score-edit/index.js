const { post, put } = require('../../utils/request');
const { validateScore, validateDate, required } = require('../../utils/validators');
const { DEFAULT_EXAM_BATCHES } = require('../../utils/constants');
const perm = require('../../utils/permission');
const options = require('../../utils/options');

Page({
  data: {
    isEdit: false,
    scoreId: '',
    form: {
      student_id: '',
      course_id: '',
      score: '',
      exam_date: '',
      exam_batch: '',
    },
    errors: {},
    loading: false,
    batchOptions: DEFAULT_EXAM_BATCHES,
    batchIndex: 0,
    canCreateScore: false,
    optionMap: {},
  },

  onLoad(options) {
    this.setData({ canCreateScore: perm.canCreateScore() });
    this.loadOptions();

    if (options.score_id) {
      // 编辑模式：从上一页传入数据
      this.setData({
        isEdit: true,
        scoreId: options.score_id,
        form: {
          student_id: options.student_id || '',
          course_id: options.course_id || '',
          score: options.score || '',
          exam_date: options.exam_date || '',
          exam_batch: options.exam_batch || '',
        },
      });
      wx.setNavigationBarTitle({ title: '修改成绩' });
    } else {
      wx.setNavigationBarTitle({ title: '录入成绩' });
    }
  },

  loadOptions() {
    options.loadOptionMap(['students', 'course_ids', 'exam_batches'])
      .then((optionMap) => {
        this.setData({ optionMap });
      });
  },

  onInput(e) {
    const field = e.currentTarget.dataset.field;
    this.setData({
      [`form.${field}`]: e.detail.value,
      [`errors.${field}`]: '',
    });
  },

  onPickFormOption(e) {
    const { type, field } = e.currentTarget.dataset;
    const index = Number(e.detail.value);
    const list = this.data.optionMap[type] || [];
    if (!list.length) {
      wx.showToast({ title: '暂无可选项，可手动输入', icon: 'none' });
      return;
    }
    const item = list[index];
    if (item) {
      this.setData({
        [`form.${field}`]: item.value,
        [`errors.${field}`]: '',
      });
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

  onDateChange(e) {
    this.setData({
      'form.exam_date': e.detail.value,
      'errors.exam_date': '',
    });
  },

  onBatchChange(e) {
    const index = parseInt(e.detail.value);
    this.setData({
      batchIndex: index,
      'form.exam_batch': this.data.batchOptions[index],
      'errors.exam_batch': '',
    });
  },

  validate() {
    const { form } = this.data;
    const errors = {};

    if (!required(form.student_id)) {
      errors.student_id = '请输入学号';
    }
    if (!required(form.course_id)) {
      errors.course_id = '请输入课程号';
    }

    const scoreResult = validateScore(form.score);
    if (!scoreResult.valid) {
      errors.score = scoreResult.message;
    }

    const dateResult = validateDate(form.exam_date);
    if (!dateResult.valid) {
      errors.exam_date = dateResult.message;
    }

    if (!required(form.exam_batch)) {
      errors.exam_batch = '请选择考试批次';
    }

    this.setData({ errors: errors });
    return Object.keys(errors).length === 0;
  },

  onSubmit() {
    if (!this.validate()) return;

    const { form, isEdit, scoreId } = this.data;
    this.setData({ loading: true });

    const payload = {
      student_id: form.student_id.trim(),
      course_id: form.course_id.trim(),
      score: parseFloat(form.score),
      exam_date: form.exam_date,
      exam_batch: form.exam_batch,
    };

    const apiCall = isEdit
      ? put(`/api/scores/${scoreId}`, payload)
      : post('/api/scores', payload);

    apiCall
      .then(() => {
        wx.showToast({
          title: isEdit ? '修改成功，统计已刷新' : '录入成功，统计已刷新',
          icon: 'success',
          duration: 2000,
        });
        setTimeout(() => {
          wx.navigateBack();
        }, 1500);
      })
      .catch((err) => {
        console.error('[ScoreEdit] 失败:', err.message);
      })
      .finally(() => {
        this.setData({ loading: false });
      });
  },

  onImport() {
    wx.navigateTo({ url: '/pages/score-import/index' });
  },
});
