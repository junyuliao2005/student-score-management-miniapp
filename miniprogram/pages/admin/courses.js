const { get, post, put } = require('../../utils/request');
const { formatCredit } = require('../../utils/format');
const { required } = require('../../utils/validators');
const options = require('../../utils/options');

Page({
  data: {
    courses: [],
    page: 1,
    pageSize: 20,
    total: 0,
    totalPages: 0,
    loading: false,

    // 表单
    showForm: false,
    formLoading: false,
    formCourseId: '',
    form: {
      course_id: '',
      course_name: '',
      teacher_id: '',
      term: '',
      credit: '3.0',
      status: 1,
    },
    statusOptions: ['启用', '停用'],
    statusIndex: 0,
  },

  onShow() {
    this.loadData();
  },

  loadData() {
    this.setData({ loading: true });

    get('/api/courses', {
      page: this.data.page,
      page_size: this.data.pageSize,
    })
      .then((data) => {
        const courses = (data.list || []).map((item) => ({
          ...item,
          creditFmt: formatCredit(item.credit),
        }));
        this.setData({
          courses: courses,
          total: data.total || 0,
          totalPages: data.total_pages || 0,
        });
      })
      .catch((err) => {
        console.error('[Courses] 加载失败:', err.message);
      })
      .finally(() => {
        this.setData({ loading: false });
      });
  },

  onAdd() {
    this.setData({
      showForm: true,
      formCourseId: '',
      form: this.getDefaultForm(),
      statusIndex: 0,
    });
  },

  getDefaultForm() {
    return {
      course_id: '',
      course_name: '',
      teacher_id: '',
      term: '',
      credit: '3.0',
      status: 1,
    };
  },

  noop() {},

  onEdit(e) {
    const item = e.currentTarget.dataset.item;
    this.setData({
      showForm: true,
      formCourseId: item.course_id,
      form: {
        course_id: item.course_id,
        course_name: item.course_name,
        teacher_id: item.teacher_id,
        term: item.term,
        credit: String(item.credit || '3.0'),
        status: item.status,
      },
      statusIndex: item.status === 1 ? 0 : 1,
    });
  },

  onFormInput(e) {
    const field = e.currentTarget.dataset.field;
    if (!field) {
      return;
    }
    this.setData({ [`form.${field}`]: e.detail.value });
  },

  onPickFormOption(e) {
    const { type, field } = e.currentTarget.dataset;
    options.showOptionPicker(type, (item) => {
      this.setData({ [`form.${field}`]: item.value });
    });
  },

  onStatusChange(e) {
    const index = parseInt(e.detail.value);
    this.setData({
      statusIndex: index,
      'form.status': index === 0 ? 1 : 0,
    });
  },

  onCloseForm() {
    this.setData({ showForm: false });
  },

  onSubmitForm() {
    const { form, formCourseId } = this.data;

    if (!required(form.course_name)) {
      wx.showToast({ title: '请输入课程名称', icon: 'none' });
      return;
    }
    if (!required(form.teacher_id)) {
      wx.showToast({ title: '请输入教师ID', icon: 'none' });
      return;
    }
    if (!required(form.term)) {
      wx.showToast({ title: '请输入学期', icon: 'none' });
      return;
    }

    if (!formCourseId && !required(form.course_id)) {
      wx.showToast({ title: '请输入课程号', icon: 'none' });
      return;
    }

    this.setData({ formLoading: true });

    const payload = {
      course_name: form.course_name,
      teacher_id: form.teacher_id,
      term: form.term,
      credit: parseFloat(form.credit) || 3.0,
      status: form.status,
    };

    if (!formCourseId) {
      payload.course_id = form.course_id;
    }

    const apiCall = formCourseId
      ? put(`/api/courses/${formCourseId}`, payload)
      : post('/api/courses', payload);

    apiCall
      .then(() => {
        wx.showToast({ title: '保存成功', icon: 'success' });
        this.setData({ showForm: false });
        this.loadData();
      })
      .catch((err) => {
        console.error('[Courses] 保存失败:', err.message);
        wx.showToast({ title: err.message || '保存失败', icon: 'none' });
      })
      .finally(() => {
        this.setData({ formLoading: false });
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
