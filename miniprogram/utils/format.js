/**
 * 格式化工具
 */

function formatScore(value) {
  if (value === null || value === undefined) return '-';
  return Number(value).toFixed(2);
}

function formatDate(dateStr) {
  if (!dateStr) return '-';
  return dateStr;
}

function formatPercent(value) {
  if (value === null || value === undefined) return '-';
  return (Number(value) * 100).toFixed(1) + '%';
}

function formatRank(rankNo) {
  if (rankNo === null || rankNo === undefined) return '-';
  return String(rankNo);
}

function formatEmpty(value) {
  if (value === null || value === undefined || value === '') return '-';
  return String(value);
}

function formatCredit(value) {
  if (value === null || value === undefined) return '-';
  return Number(value).toFixed(1);
}

module.exports = {
  formatScore,
  formatDate,
  formatPercent,
  formatRank,
  formatEmpty,
  formatCredit,
};
