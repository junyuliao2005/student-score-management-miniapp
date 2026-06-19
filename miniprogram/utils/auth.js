/**
 * 登录态管理
 */

function normalizeArray(value) {
  if (Array.isArray(value)) {
    return value;
  }
  if (value === null || value === undefined || value === '') {
    return [];
  }
  return [value];
}

function saveLoginInfo(token, user, roles, permissions) {
  wx.setStorageSync('token', token);
  wx.setStorageSync('user', user || {});
  wx.setStorageSync('roles', normalizeArray(roles));
  wx.setStorageSync('permissions', normalizeArray(permissions));
}

function getToken() {
  return wx.getStorageSync('token') || '';
}

function getUser() {
  return wx.getStorageSync('user') || null;
}

function getRoles() {
  return normalizeArray(wx.getStorageSync('roles'));
}

function getPermissions() {
  return normalizeArray(wx.getStorageSync('permissions'));
}

function isLoggedIn() {
  return !!getToken();
}

function logout() {
  wx.removeStorageSync('token');
  wx.removeStorageSync('user');
  wx.removeStorageSync('roles');
  wx.removeStorageSync('permissions');
}

function hasRole(role) {
  const roles = getRoles();
  return roles.includes(role);
}

function hasPermission(permission) {
  const permissions = getPermissions();
  return permissions.includes(permission);
}

module.exports = {
  saveLoginInfo,
  getToken,
  getUser,
  getRoles,
  getPermissions,
  isLoggedIn,
  logout,
  hasRole,
  hasPermission,
  normalizeArray,
};
