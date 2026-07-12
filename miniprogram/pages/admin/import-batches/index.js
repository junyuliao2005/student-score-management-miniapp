const { get, post } = require('../../../utils/request');

Page({
  data: {
    loading: false,
    actionLoading: false,
    errorMsg: '',
    batches: [],
    page: 1,
    pageSize: 20,
    totalPages: 0,
    importType: '',
    status: '',
    importTypeOptions: [{ label: '全部类型', value: '' }],
    statusOptions: [{ label: '全部状态', value: '' }],
    importTypeIndex: 0,
    statusIndex: 0,
    detail: null,
    showDetail: false,
  },

  onShow() {
    this.loadData();
  },

  loadData() {
    if (this.data.loading) return;
    this.setData({ loading: true, errorMsg: '' });
    get('/api/import-batches', {
      page: this.data.page,
      page_size: this.data.pageSize,
      import_type: this.data.importType || undefined,
      status: this.data.status || undefined,
    })
      .then((data) => {
        const filters = data.filter_options || {};
        this.setData({
          batches: (Array.isArray(data.list) ? data.list : []).map((item) => this.decorateBatch(item)),
          totalPages: data.total_pages || 0,
          importTypeOptions: this.buildOptions(filters.import_types, '全部类型'),
          statusOptions: this.buildOptions(filters.statuses, '全部状态'),
        });
      })
      .catch((err) => this.setData({ errorMsg: err.message || '导入批次加载失败' }))
      .finally(() => this.setData({ loading: false }));
  },

  buildOptions(values, allLabel) {
    return [{ label: allLabel, value: '' }].concat(
      (Array.isArray(values) ? values : []).map((value) => ({ label: this.displayValue(value), value })),
    );
  },

  decorateBatch(item) {
    return {
      ...item,
      typeText: item.import_type === 'scores' ? '成绩导入' : item.import_type === 'users' ? '学生导入' : item.import_type,
      statusText: this.displayValue(item.status),
    };
  },

  displayValue(value) {
    const labels = {
      completed: '已完成',
      processing: '处理中',
      rolled_back: '已撤销',
      rollback_partial: '部分撤销',
      failed: '失败',
      scores: '成绩导入',
      users: '学生导入',
    };
    return labels[value] || value || '-';
  },

  onTypeChange(e) {
    const index = Number(e.detail.value) || 0;
    this.setData({ importTypeIndex: index, importType: this.data.importTypeOptions[index].value, page: 1 });
    this.loadData();
  },

  onStatusChange(e) {
    const index = Number(e.detail.value) || 0;
    this.setData({ statusIndex: index, status: this.data.statusOptions[index].value, page: 1 });
    this.loadData();
  },

  onViewDetail(e) {
    const id = e.currentTarget.dataset.id;
    this.setData({ actionLoading: true, errorMsg: '' });
    get(`/api/import-batches/${id}`)
      .then((detail) => this.setData({ detail: this.decorateBatch(detail), showDetail: true }))
      .catch((err) => this.setData({ errorMsg: err.message || '批次详情加载失败' }))
      .finally(() => this.setData({ actionLoading: false }));
  },

  onCloseDetail() {
    if (!this.data.actionLoading) this.setData({ showDetail: false, detail: null });
  },

  onRollback() {
    const detail = this.data.detail;
    if (!detail || detail.status !== 'completed' || this.data.actionLoading) return;
    wx.showModal({
      title: '确认安全撤销',
      content: '仅撤销本批次创建且未被后续修改的数据；有业务引用或已修改记录会跳过。是否继续？',
      confirmText: '执行撤销',
      success: (res) => {
        if (!res.confirm) return;
        this.executeRollback(detail.import_batch_id);
      },
    });
  },

  executeRollback(id) {
    this.setData({ actionLoading: true, errorMsg: '' });
    post(`/api/import-batches/${id}/rollback`, {})
      .then((result) => {
        const decorated = this.decorateBatch({ ...this.data.detail, ...result });
        this.setData({ detail: decorated });
        wx.showToast({
          title: `撤销${result.success_count || 0}，跳过${result.skipped_count || 0}`,
          icon: 'none',
          duration: 2500,
        });
        this.loadData();
      })
      .catch((err) => this.setData({ errorMsg: err.message || '安全撤销失败' }))
      .finally(() => this.setData({ actionLoading: false }));
  },

  onPrevPage() {
    if (this.data.page > 1) this.setData({ page: this.data.page - 1 }, () => this.loadData());
  },

  onNextPage() {
    if (this.data.page < this.data.totalPages) this.setData({ page: this.data.page + 1 }, () => this.loadData());
  },
});
