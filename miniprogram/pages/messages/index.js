const { get, post, put } = require('../../utils/request');
const auth = require('../../utils/auth');

Page({
  data: {
    roles: [],
    isAdmin: false,
    messages: [],
    contacts: [],
    receiverIndex: 0,
    receiverId: '',
    receiverLabel: '',
    title: '',
    content: '',
    courseId: '',
    examBatch: '',
    box: 'received',
    page: 1,
    pageSize: 20,
    totalPages: 0,
    unreadCount: 0,
    loading: false,
    contactsLoading: false,
    contactsLoaded: false,
    contactError: '',
    sending: false,
    errorMsg: '',
  },

  onShow() {
    if (!auth.isLoggedIn()) {
      wx.reLaunch({ url: '/pages/login/index' });
      return;
    }

    const roles = auth.getRoles();
    const defaultBox = roles.includes('admin') ? 'all' : 'received';
    this.setData({ roles: roles, isAdmin: roles.includes('admin'), box: this.data.box || defaultBox });
    this.loadContacts();
    this.loadUnreadCount();
    this.loadMessages();
  },

  loadMessages() {
    this.setData({ loading: true, errorMsg: '' });

    const params = {
      page: this.data.page,
      page_size: this.data.pageSize,
    };
    if (this.data.box === 'unread') {
      params.unread_only = 1;
    } else if (this.data.box !== 'all') {
      params.box = this.data.box;
    }

    get('/api/messages', params)
      .then((data) => {
        this.setData({
          messages: data.list || [],
          totalPages: data.total_pages || 0,
        });
      })
      .catch((err) => {
        this.setData({ errorMsg: err.message || '留言加载失败' });
      })
      .finally(() => {
        this.setData({ loading: false });
      });
  },

  loadUnreadCount() {
    get('/api/messages/unread-count', {}, { showError: false })
      .then((data) => {
        this.setData({ unreadCount: data.unread_count || 0 });
      })
      .catch(() => {});
  },

  loadContacts() {
    this.setData({ contactsLoading: true, contactsLoaded: false, contactError: '' });
    get('/api/messages/contacts', {}, { showError: false })
      .then((data) => {
        const roles = this.data.roles;
        const contacts = roles.includes('student') && !roles.includes('teacher') && !roles.includes('admin')
          ? (data.teachers || [])
          : (data.students || []);
        this.setData({
          contacts: contacts,
          receiverId: contacts[0] ? contacts[0].user_id : '',
          receiverLabel: contacts[0] ? `${contacts[0].real_name}（${contacts[0].user_id}）` : '',
          receiverIndex: 0,
          contactsLoaded: true,
          contactError: '',
        });
      })
      .catch((err) => {
        this.setData({
          contacts: [],
          receiverId: '',
          receiverLabel: '',
          receiverIndex: 0,
          contactsLoaded: true,
          contactError: err.message || '接收人加载失败，请重试',
        });
      })
      .finally(() => {
        this.setData({ contactsLoading: false });
      });
  },

  onReloadContacts() {
    this.loadContacts();
  },

  onBoxChange(e) {
    const box = e.currentTarget.dataset.box;
    this.setData({ box: box, page: 1 });
    this.loadMessages();
  },

  onReceiverChange(e) {
    const index = Number(e.detail.value);
    const contact = this.data.contacts[index];
    this.setData({
      receiverIndex: index,
      receiverId: contact ? contact.user_id : '',
      receiverLabel: contact ? `${contact.real_name}（${contact.user_id}）` : '',
    });
  },

  onInput(e) {
    const field = e.currentTarget.dataset.field;
    this.setData({ [field]: e.detail.value, errorMsg: '' });
  },

  onSend() {
    const { receiverId, title, content, courseId, examBatch } = this.data;
    if (!receiverId) {
      this.setData({ errorMsg: '请选择接收人' });
      wx.showToast({ title: '请先选择接收人', icon: 'none' });
      return;
    }
    if (!title.trim()) {
      this.setData({ errorMsg: '请输入标题' });
      return;
    }
    if (!content.trim()) {
      this.setData({ errorMsg: '请输入留言内容' });
      return;
    }

    this.setData({ sending: true, errorMsg: '' });
    post('/api/messages', {
      receiver_id: receiverId,
      title: title.trim(),
      content: content.trim(),
      course_id: courseId.trim() || undefined,
      exam_batch: examBatch.trim() || undefined,
    })
      .then(() => {
        wx.showToast({ title: '发送成功', icon: 'success' });
        this.setData({
          title: '',
          content: '',
          courseId: '',
          examBatch: '',
          box: 'sent',
          page: 1,
        });
        this.loadMessages();
      })
      .catch((err) => {
        this.setData({ errorMsg: err.message || '发送失败' });
      })
      .finally(() => {
        this.setData({ sending: false });
      });
  },

  onMessageTap(e) {
    const item = e.currentTarget.dataset.item;
    if (!item || item.is_read) {
      return;
    }

    put(`/api/messages/${item.message_id}/read`)
      .then(() => {
        this.loadUnreadCount();
        this.loadMessages();
      })
      .catch(() => {});
  },

  onReadAll() {
    put('/api/messages/read-all')
      .then((data) => {
        wx.showToast({ title: `已读 ${data.updated_count || 0} 条`, icon: 'none' });
        this.loadUnreadCount();
        this.loadMessages();
      })
      .catch((err) => {
        this.setData({ errorMsg: err.message || '标记已读失败' });
      });
  },

  onPrevPage() {
    if (this.data.page > 1) {
      this.setData({ page: this.data.page - 1 });
      this.loadMessages();
    }
  },

  onNextPage() {
    if (this.data.page < this.data.totalPages) {
      this.setData({ page: this.data.page + 1 });
      this.loadMessages();
    }
  },
});
