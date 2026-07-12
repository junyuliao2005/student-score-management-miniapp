const { post } = require('../../utils/request');
const upload = require('../../utils/upload');
const auth = require('../../utils/auth');
const perm = require('../../utils/permission');

Page({
  data: {
    fileName: '',
    preview: null,
    uploading: false,
    confirming: false,
    errorRows: [],
    duplicateRows: [],
    validRows: [],
    importDone: false,
    errorMsg: '',
  },

  onShow() {
    if (!auth.isLoggedIn()) {
      wx.reLaunch({ url: '/pages/login/index' });
      return;
    }

    if (!perm.canCreateScore()) {
      wx.showToast({ title: '无权限批量导入成绩', icon: 'none' });
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
          errorRows: [],
          duplicateRows: [],
          validRows: [],
          importDone: false,
          errorMsg: '',
        });
        this.uploadPreview(file.path, file.name);
      },
    });
  },

  uploadPreview(filePath, fileName) {
    this.setData({ uploading: true, errorMsg: '' });
    const task = upload.uploadFile({
      filePath,
      fileName,
      fieldName: 'file',
      localPath: '/api/scores/import/preview',
      cloudPath: '/api/uploads/cloud/scores/import/preview',
      cloudKind: 'score-imports',
    });
    task.promise
      .then((data) => {
        const preview = data || {};
        const rows = (preview.rows || []).map((row) => ({
          ...row,
          errorText: (Array.isArray(row.errors) ? row.errors : []).join('；'),
        }));
        preview.rows = rows;
        this.setData({
          preview: preview,
          validRows: rows.filter((row) => row.status === 'valid'),
          errorRows: rows.filter((row) => row.status === 'error'),
          duplicateRows: rows.filter((row) => row.status === 'duplicate'),
          importDone: false,
        });
        wx.showToast({ title: '预览完成', icon: 'success' });
      })
      .catch((err) => {
        this.setData({ errorMsg: err.message || '文件上传失败，请检查网络' });
      })
      .finally(() => {
        this.setData({ uploading: false });
      });
  },

  onConfirmImport() {
    const { preview } = this.data;
    if (!preview || !preview.import_id) {
      this.setData({ errorMsg: '请先选择 Excel 文件并完成预览' });
      return;
    }

    if ((preview.valid_rows || 0) <= 0) {
      this.setData({ errorMsg: '没有可导入的合法成绩' });
      return;
    }

    wx.showModal({
      title: '确认导入',
      content: `将导入 ${preview.valid_rows} 条合法成绩，重复和错误行会跳过。`,
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

    post('/api/scores/import/confirm', { import_id: importId })
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

  onBackToList() {
    wx.navigateBack();
  },
});
