/**
 * 权限检查工具
 */
const auth = require('./auth');

function isStudent() {
  return auth.hasRole('student');
}

function isTeacher() {
  return auth.hasRole('teacher');
}

function isAdmin() {
  return auth.hasRole('admin');
}

function isParent() {
  return auth.hasRole('parent');
}

function canCreateScore() {
  return auth.hasPermission('score:create');
}

function canUpdateScore() {
  return auth.hasPermission('score:update');
}

function canReadAllScores() {
  return auth.hasPermission('score:read:all');
}

function canReadSelfScore() {
  return auth.hasPermission('score:read:self');
}

function canUseScoreList() {
  return (isTeacher() || isAdmin()) && canReadAllScores();
}

function canUseStats() {
  return (isTeacher() || isAdmin()) && canReadStats();
}

function canUseMyScores() {
  return isStudent() && canReadSelfScore();
}

function canReadStats() {
  return auth.hasPermission('stats:read');
}

function canReadWarnings() {
  return auth.hasPermission('warning:read');
}

function canRefreshStats() {
  return auth.hasPermission('stats:evaluate');
}

function canRefreshWarnings() {
  return auth.hasPermission('warning:refresh');
}

function canManageUsers() {
  return auth.hasPermission('user:manage');
}

function canManageCourses() {
  return auth.hasPermission('course:manage');
}

function canManageConfigs() {
  return auth.hasPermission('config:manage');
}

function canReadLogs() {
  return auth.hasPermission('log:read');
}

function canAiAdvice() {
  return auth.hasPermission('ai:student_advice:self') || auth.hasPermission('ai:student_advice:all');
}

function canAiClass() {
  return auth.hasPermission('ai:class_overview');
}

function canAiExam() {
  return auth.hasPermission('ai:exam_analyze');
}

module.exports = {
  isStudent,
  isTeacher,
  isAdmin,
  isParent,
  canCreateScore,
  canUpdateScore,
  canReadAllScores,
  canReadSelfScore,
  canUseScoreList,
  canUseStats,
  canUseMyScores,
  canReadStats,
  canReadWarnings,
  canRefreshStats,
  canRefreshWarnings,
  canManageUsers,
  canManageCourses,
  canManageConfigs,
  canReadLogs,
  canAiAdvice,
  canAiClass,
  canAiExam,
};
