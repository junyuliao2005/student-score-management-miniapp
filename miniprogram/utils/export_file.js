function openBase64File(payload) {
  return new Promise((resolve, reject) => {
    if (!payload || !payload.content_base64) {
      reject(new Error('导出文件内容为空'));
      return;
    }
    const filename = sanitizeFilename(payload.filename || 'export.bin');
    const extension = (filename.split('.').pop() || '').toLowerCase();
    const filePath = `${wx.env.USER_DATA_PATH}/${filename}`;
    wx.getFileSystemManager().writeFile({
      filePath,
      data: payload.content_base64,
      encoding: 'base64',
      success() {
        wx.openDocument({
          filePath,
          fileType: extension,
          showMenu: true,
          success: resolve,
          fail: reject,
        });
      },
      fail: reject,
    });
  });
}

function sanitizeFilename(value) {
  const name = String(value || '').replace(/[\\/:*?"<>|]/g, '-').slice(0, 120);
  return name || 'export.bin';
}

module.exports = { openBase64File };
