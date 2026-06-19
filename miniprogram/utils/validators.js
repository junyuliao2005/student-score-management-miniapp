/**
 * 表单校验工具
 */

function required(value) {
  if (value === undefined || value === null) return false;
  return String(value).trim().length > 0;
}

function validateScore(score) {
  if (score === '' || score === undefined || score === null) {
    return { valid: false, message: '请输入分数' };
  }
  const num = Number(score);
  if (isNaN(num)) {
    return { valid: false, message: '分数必须为数字' };
  }
  if (num < 0 || num > 100) {
    return { valid: false, message: '分数必须在 0 到 100 之间' };
  }
  return { valid: true, message: '' };
}

function validateDate(date) {
  if (!date) {
    return { valid: false, message: '请选择日期' };
  }
  const regex = /^\d{4}-\d{2}-\d{2}$/;
  if (!regex.test(date)) {
    return { valid: false, message: '日期格式必须为 YYYY-MM-DD' };
  }
  return { valid: true, message: '' };
}

function validatePage(page, pageSize) {
  const p = parseInt(page) || 1;
  const ps = parseInt(pageSize) || 20;
  return {
    page: p < 1 ? 1 : p,
    pageSize: ps < 1 ? 1 : (ps > 100 ? 100 : ps),
  };
}

module.exports = {
  required,
  validateScore,
  validateDate,
  validatePage,
};
