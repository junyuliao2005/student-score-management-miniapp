const { get, post, put } = require('../../utils/request');
const { ROLE_NAMES } = require('../../utils/constants');
const { required } = require('../../utils/validators');
const options = require('../../utils/options');

Page({
  data: {
    users: [],
    page: 1,
    pageSize: 20,
    total: 0,
    totalPages: 0,
    loading: false,

    // 表单
    showForm: false,
    formLoading: false,
    formUserId: '',
    form: {
      user_id: '',
      username: '',
      password: '',
      real_name: '',
      class_name: '',
      role: 'student',
      status: 1,
    },
    roleOptions: ['学生', '教师', '管理员'],
    roleIndex: 0,
    statusOptions: ['启用', '停用'],
    statusIndex: 0,
  },

  onShow() {
    this.loadData();
  },

  loadData() {
    this.setData({ loading: true });

    get('/api/users', {
      page: this.data.page,
      page_size: this.data.pageSize,
    })
      .then((data) => {
        const users = (Array.isArray(data.list) ? data.list : []).map((item) => {
          const roles = Array.isArray(item.roles) ? item.roles : [];
          return {
            ...item,
            roleNames: roles.map((r) => ROLE_NAMES[r] || r).join(', ') || '-',
          };
        });
        this.setData({
          users: users,
          total: data.total || 0,
          totalPages: data.total_pages || 0,
        });
      })
      .catch((err) => {
        console.error('[Users] 加载失败:', err.message);
      })
      .finally(() => {
        this.setData({ loading: false });
      });
  },

  onAdd() {
    this.setData({
      showForm: true,
      formUserId: '',
      form: {
        user_id: '',
        username: '',
        password: '',
        real_name: '',
        class_name: '',
        role: 'student',
        status: 1,
      },
      roleIndex: 0,
      statusIndex: 0,
    });
  },

  onImportUsers() {
    wx.navigateTo({ url: '/pages/admin/import-users/index' });
  },

  onEdit(e) {
    const item = e.currentTarget.dataset.item;
    const roles = Array.isArray(item.roles) ? item.roles : [];
    const roleMap = { student: 0, teacher: 1, admin: 2 };
    const roleIndex = roleMap[roles[0]] || 0;

    this.setData({
      showForm: true,
      formUserId: item.user_id,
      form: {
        user_id: item.user_id,
        username: item.username,
        password: '',
        real_name: item.real_name,
        class_name: item.class_name || '',
        role: roles[0] || 'student',
        status: item.status,
      },
      roleIndex: roleIndex,
      statusIndex: item.status === 1 ? 0 : 1,
    });
  },

  onFormInput(e) {
    const field = e.currentTarget.dataset.field;
    this.setData({ [`form.${field}`]: e.detail.value });
  },

  onPickFormOption(e) {
    const { type, field } = e.currentTarget.dataset;
    options.showOptionPicker(type, (item) => {
      this.setData({ [`form.${field}`]: item.value });
    });
  },

  onRoleChange(e) {
    const index = parseInt(e.detail.value);
    const roleMap = ['student', 'teacher', 'admin'];
    this.setData({
      roleIndex: index,
      'form.role': roleMap[index],
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
    const { form, formUserId } = this.data;

    if (!required(form.real_name)) {
      wx.showToast({ title: '请输入真实姓名', icon: 'none' });
      return;
    }

    if (!formUserId) {
      // 新增
      if (!required(form.user_id)) {
        wx.showToast({ title: '请输入用户ID', icon: 'none' });
        return;
      }
      if (!required(form.username)) {
        wx.showToast({ title: '请输入用户名', icon: 'none' });
        return;
      }
      if (!required(form.password)) {
        wx.showToast({ title: '请输入密码', icon: 'none' });
        return;
      }
    }

    this.setData({ formLoading: true });

    const payload = {
      real_name: form.real_name,
      class_name: form.class_name || undefined,
      role: form.role,
      status: form.status,
    };

    if (!formUserId) {
      payload.user_id = form.user_id;
      payload.username = form.username;
      payload.password = form.password;
    }

    const apiCall = formUserId
      ? put(`/api/users/${formUserId}`, payload)
      : post('/api/users', payload);

    apiCall
      .then(() => {
        wx.showToast({ title: '保存成功', icon: 'success' });
        this.setData({ showForm: false });
        this.loadData();
      })
      .catch((err) => {
        console.error('[Users] 保存失败:', err.message);
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
