const { get, put } = require('../../../utils/request');

Page({
  data: {
    loading: false,
    saving: false,
    errorMsg: '',
    teachers: [],
    teacherIndex: 0,
    selectedTeacherId: '',
    classOptions: [],
    courseOptions: [],
    bindings: [],
  },

  onShow() {
    this.loadData();
  },

  loadData() {
    if (this.data.loading) return;
    this.setData({ loading: true, errorMsg: '' });
    Promise.all([
      get('/api/options', { type: 'teachers' }),
      get('/api/options', { type: 'classes' }),
      get('/api/options', { type: 'courses' }),
      get('/api/admin/teacher-bindings'),
    ])
      .then(([teacherData, classData, courseData, bindingData]) => {
        const teachers = this.normalizeOptions(teacherData.options);
        const selectedTeacherId = this.data.selectedTeacherId || (teachers[0] && teachers[0].value) || '';
        const teacherIndex = Math.max(0, teachers.findIndex((item) => item.value === selectedTeacherId));
        this.setData({
          teachers,
          teacherIndex,
          selectedTeacherId,
          classOptions: this.normalizeOptions(classData.options),
          courseOptions: this.normalizeOptions(courseData.options),
          bindings: Array.isArray(bindingData.list) ? bindingData.list : [],
        });
        this.applyBindingSelection();
      })
      .catch((err) => {
        this.setData({ errorMsg: err.message || '教师绑定加载失败' });
      })
      .finally(() => this.setData({ loading: false }));
  },

  normalizeOptions(values) {
    return (Array.isArray(values) ? values : []).map((item) => ({
      label: String(item.label || item.value || ''),
      value: String(item.value || ''),
      checked: false,
    })).filter((item) => item.value);
  },

  onTeacherChange(e) {
    const teacherIndex = Number(e.detail.value) || 0;
    const selected = this.data.teachers[teacherIndex];
    this.setData({ teacherIndex, selectedTeacherId: selected ? selected.value : '' });
    this.applyBindingSelection();
  },

  applyBindingSelection() {
    const binding = this.data.bindings.find((item) => item.teacher_id === this.data.selectedTeacherId) || {};
    const selectedClasses = new Set(Array.isArray(binding.class_names) ? binding.class_names : []);
    const selectedCourses = new Set((Array.isArray(binding.courses) ? binding.courses : []).map((item) => item.course_id));
    this.setData({
      classOptions: this.data.classOptions.map((item) => ({ ...item, checked: selectedClasses.has(item.value) })),
      courseOptions: this.data.courseOptions.map((item) => ({ ...item, checked: selectedCourses.has(item.value) })),
    });
  },

  onClassesChange(e) {
    const selected = new Set(e.detail.value || []);
    this.setData({ classOptions: this.data.classOptions.map((item) => ({ ...item, checked: selected.has(item.value) })) });
  },

  onCoursesChange(e) {
    const selected = new Set(e.detail.value || []);
    this.setData({ courseOptions: this.data.courseOptions.map((item) => ({ ...item, checked: selected.has(item.value) })) });
  },

  onSave() {
    const teacherId = this.data.selectedTeacherId;
    if (!teacherId) {
      wx.showToast({ title: '请先选择教师', icon: 'none' });
      return;
    }
    if (this.data.saving) return;
    const classNames = this.data.classOptions.filter((item) => item.checked).map((item) => item.value);
    const courseIds = this.data.courseOptions.filter((item) => item.checked).map((item) => item.value);
    this.setData({ saving: true, errorMsg: '' });
    put(`/api/admin/teacher-bindings/${encodeURIComponent(teacherId)}`, {
      class_names: classNames,
      course_ids: courseIds,
    })
      .then((saved) => {
        const bindings = this.data.bindings.filter((item) => item.teacher_id !== teacherId);
        bindings.push(saved);
        this.setData({ bindings });
        this.applyBindingSelection();
        wx.showToast({ title: '绑定已保存', icon: 'success' });
      })
      .catch((err) => this.setData({ errorMsg: err.message || '保存失败' }))
      .finally(() => this.setData({ saving: false }));
  },
});
