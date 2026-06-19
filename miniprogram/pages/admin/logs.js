const { get } = require('../../utils/request');

Page({
  data: {
    logs: [],
    page: 1,
    pageSize: 20,
    total: 0,
    totalPages: 0,
    loading: false,
  },

  onShow() {
    this.loadData();
  },

  loadData() {
    this.setData({ loading: true });

    get('/api/admin/logs', {
      page: this.data.page,
      page_size: this.data.pageSize,
    })
      .then((data) => {
        this.setData({
          logs: data.list || [],
          total: data.total || 0,
          totalPages: data.total_pages || 0,
        });
      })
      .catch((err) => {
        console.error('[Logs] 加载失败:', err.message);
      })
      .finally(() => {
        this.setData({ loading: false });
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
