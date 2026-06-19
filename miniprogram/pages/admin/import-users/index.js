const { BASE_URL, post } = require('../../../utils/request');
const auth = require('../../../utils/auth');

Page({
  data: {
    fileName: '',
    preview: null,
    uploading: false,
    confirming: false,
    validRows: [],
    duplicateRows: [],
    errorRows: [],
    importDone: false,
    errorMsg: '',
  },

  onShow() {
    if (!auth.isLoggedIn()) {
      wx.reLaunch({ url: '/pages/login/index' });
      return;
    }

    if (!auth.hasRole('admin')) {
      wx.showToast({ title: '仅管理员可批量导入学生', icon: 'none' });
      wx.switchTab({ url: '/pages/home/index' });
    }
  },

  onChooseFile() {
    wx.chooseMessageFile({
      count: 1,
      type: 'file',
      extension: ['xlsx'],
      success: (res) => {
        const file = (res.tempFiles || [])[0];
        if (!file) {
          return;
        }

        if (!file.name || !file.name.toLowerCase().endsWith('.xlsx')) {
          wx.showToast({ title: '仅支持 .xlsx 文件', icon: 'none' });
          return;
        }

        this.setData({
          fileName: file.name,
          preview: null,
          validRows: [],
          duplicateRows: [],
          errorRows: [],
          importDone: false,
          errorMsg: '',
        });
        this.uploadPreview(file.path);
      },
    });
  },

  uploadPreview(filePath) {
    const token = wx.getStorageSync('token') || '';
    this.setData({ uploading: true, errorMsg: '' });

    // TODO: 体验版普通接口已切换 callContainer，文件上传后续可改为云存储上传后再调用后端解析，
    // 或绑定自定义域名后继续使用 wx.uploadFile。
    wx.uploadFile({
      url: `${BASE_URL}/api/users/import/preview`,
      filePath: filePath,
      name: 'file',
      header: {
        Authorization: token ? `Bearer ${token}` : '',
      },
      success: (res) => {
        let body = null;
        try {
          body = JSON.parse(res.data);
        } catch (err) {
          this.setData({ errorMsg: '导入预览响应解析失败' });
          return;
        }

        if (res.statusCode !== 200 || body.code !== 0) {
          this.setData({ errorMsg: body.message || `导入预览失败(${res.statusCode})` });
          return;
        }

        const preview = body.data || {};
        const rows = (preview.rows || []).map((row) => ({
          ...row,
          errorText: (Array.isArray(row.errors) ? row.errors : []).join('；'),
        }));
        preview.rows = rows;
        this.setData({
          preview: preview,
          validRows: rows.filter((row) => row.status === 'valid'),
          duplicateRows: rows.filter((row) => row.status === 'duplicate'),
          errorRows: rows.filter((row) => row.status === 'error'),
          importDone: false,
        });
        wx.showToast({ title: '预览完成', icon: 'success' });
      },
      fail: () => {
        this.setData({ errorMsg: '文件上传失败，请检查网络' });
      },
      complete: () => {
        this.setData({ uploading: false });
      },
    });
  },

  onConfirmImport() {
    const { preview } = this.data;
    if (!preview || !preview.import_id) {
      this.setData({ errorMsg: '请先选择 Excel 文件并完成预览' });
      return;
    }

    if ((preview.valid_rows || 0) <= 0) {
      this.setData({ errorMsg: '没有可导入的合法学生信息' });
      return;
    }

    wx.showModal({
      title: '确认导入',
      content: `将导入 ${preview.valid_rows} 条学生信息，重复和错误行会跳过。默认角色为学生。`,
      success: (res) => {
        if (!res.confirm) {
          return;
        }
        this.confirmImport(preview.import_id);
      },
    });
  },

  confirmImport(importId) {
    this.setData({ confirming: true, errorMsg: '' });

    post('/api/users/import/confirm', { import_id: importId })
      .then((data) => {
        wx.showToast({ title: '导入完成', icon: 'success' });
        this.setData({
          importDone: true,
          preview: {
            ...this.data.preview,
            confirmResult: data,
          },
        });
      })
      .catch((err) => {
        this.setData({ errorMsg: err.message || '确认导入失败' });
      })
      .finally(() => {
        this.setData({ confirming: false });
      });
  },

  onBack() {
    wx.navigateBack();
  },
});
