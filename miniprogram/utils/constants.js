/**
 * 常量定义
 */

// 角色枚举
const ROLES = {
  STUDENT: 'student',
  TEACHER: 'teacher',
  ADMIN: 'admin',
  PARENT: 'parent',
};

// 角色中文名
const ROLE_NAMES = {
  student: '学生',
  teacher: '教师',
  admin: '管理员',
  parent: '家长',
};

// 等级标签样式类
const LEVEL_TAG_CLASS = {
  '优秀': 'tag-excellent',
  '良好': 'tag-good',
  '中等': 'tag-medium',
  '及格': 'tag-pass',
  '不及格': 'tag-fail',
};

// 预警类型中文名
const WARNING_TYPE_NAMES = {
  'low_score': '低分预警',
  'subject_bias': '偏科预警',
};

// 预警类型样式类
const WARNING_TAG_CLASS = {
  'low_score': 'tag-warning-low',
  'subject_bias': 'tag-warning-bias',
};

// 默认学期
const DEFAULT_TERM = '2025-2026-2';

// 默认考试批次
const DEFAULT_EXAM_BATCHES = ['期中', '期末', '月考', '随堂测验'];

// 错误码映射
const ERROR_MESSAGES = {
  20001: '分数超出范围',
  20002: '成绩记录重复',
  20003: '课程不存在',
  20004: '学生不存在',
  20005: '配置缺失',
  30001: '权限不足',
  40001: 'Token 已过期',
  40002: 'Token 无效',
  40003: '请先登录',
  50001: '数据库操作失败',
  50002: '统计刷新失败',
  50003: '服务器内部错误',
};

module.exports = {
  ROLES,
  ROLE_NAMES,
  LEVEL_TAG_CLASS,
  WARNING_TYPE_NAMES,
  WARNING_TAG_CLASS,
  DEFAULT_TERM,
  DEFAULT_EXAM_BATCHES,
  ERROR_MESSAGES,
};
