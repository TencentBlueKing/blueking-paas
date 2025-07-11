/* eslint-disable no-param-reassign, no-underscore-dangle */
/**
 * 安全对象操作工具类
 * 防止原型污染攻击、toString 替换攻击等安全风险
 */

// 危险属性名黑名单
const DANGEROUS_KEYS = [
  '__proto__',
  'constructor',
  'prototype',
  'toString',
  'valueOf',
  'hasOwnProperty',
  'isPrototypeOf',
  'propertyIsEnumerable',
  'toLocaleString',
];

/**
 * 检查属性名是否安全
 * @param {string} key - 属性名
 * @returns {boolean} 是否安全
 */
export function isSafeKey(key) {
  if (typeof key !== 'string' || !key) {
    return false;
  }

  // 检查是否包含危险关键字
  if (DANGEROUS_KEYS.includes(key)) {
    return false;
  }

  // 检查是否以双下划线开头（通常是内部属性）
  if (key.startsWith('__')) {
    return false;
  }

  return true;
}

/**
 * 创建安全的无原型对象
 * @param {Object} source - 源对象（可选）
 * @returns {Object} 无原型对象
 */
export function createSafeObject(source = {}) {
  const safeObj = Object.create(null);

  if (source && typeof source === 'object') {
    Object.keys(source).forEach((key) => {
      if (isSafeKey(key)) {
        safeObj[key] = source[key];
      }
    });
  }

  return safeObj;
}

/**
 * 安全地设置对象属性
 * @param {Object} obj - 目标对象
 * @param {string} key - 属性名
 * @param {*} value - 属性值
 * @returns {boolean} 是否设置成功
 */
export function safeSet(obj, key, value) {
  if (!obj || typeof obj !== 'object') {
    return false;
  }

  if (!isSafeKey(key)) {
    console.warn(`[Security] Blocked potentially dangerous key: ${key}`);
    return false;
  }

  // 确保对象是安全的（无原型或已经是安全对象）
  if (Object.getPrototypeOf(obj) !== null && !obj.__isSafeObject) {
    console.warn('[Security] Attempting to set property on potentially unsafe object');
    return false;
  }

  obj[key] = value;
  return true;
}

/**
 * 安全地获取对象属性
 * @param {Object} obj - 源对象
 * @param {string} key - 属性名
 * @param {*} defaultValue - 默认值
 * @returns {*} 属性值
 */
export function safeGet(obj, key, defaultValue = undefined) {
  if (!obj || typeof obj !== 'object') {
    return defaultValue;
  }

  if (!isSafeKey(key)) {
    console.warn(`[Security] Blocked potentially dangerous key access: ${key}`);
    return defaultValue;
  }

  return Object.prototype.hasOwnProperty.call(obj, key) ? obj[key] : defaultValue;
}

/**
 * 安全地检查对象是否包含某个属性
 * @param {Object} obj - 源对象
 * @param {string} key - 属性名
 * @returns {boolean} 是否包含该属性
 */
export function safeHas(obj, key) {
  if (!obj || typeof obj !== 'object') {
    return false;
  }

  if (!isSafeKey(key)) {
    return false;
  }

  return Object.prototype.hasOwnProperty.call(obj, key);
}

/**
 * 安全地删除对象属性
 * @param {Object} obj - 目标对象
 * @param {string} key - 属性名
 * @returns {boolean} 是否删除成功
 */
export function safeDelete(obj, key) {
  if (!obj || typeof obj !== 'object') {
    return false;
  }

  if (!isSafeKey(key)) {
    console.warn(`[Security] Blocked potentially dangerous key deletion: ${key}`);
    return false;
  }

  if (Object.prototype.hasOwnProperty.call(obj, key)) {
    delete obj[key];
    return true;
  }

  return false;
}

/**
 * 将普通对象转换为安全对象
 * @param {Object} obj - 源对象
 * @returns {Object} 安全对象
 */
export function toSafeObject(obj) {
  if (!obj || typeof obj !== 'object') {
    return createSafeObject();
  }

  const safeObj = createSafeObject();
  safeObj.__isSafeObject = true;

  Object.keys(obj).forEach((key) => {
    if (isSafeKey(key)) {
      if (typeof obj[key] === 'object' && obj[key] !== null) {
        // 递归处理嵌套对象
        safeObj[key] = toSafeObject(obj[key]);
      } else {
        safeObj[key] = obj[key];
      }
    }
  });

  return safeObj;
}

/**
 * 验证 appCode 的安全性（专门为应用代码验证）
 * @param {string} appCode - 应用代码
 * @returns {boolean} 是否安全
 */
export function validateAppCode(appCode) {
  if (typeof appCode !== 'string' || !appCode) {
    return false;
  }

  // 长度限制
  if (appCode.length > 64) {
    return false;
  }

  // 只允许字母、数字、下划线、短横线
  if (!/^[a-zA-Z0-9_-]+$/.test(appCode)) {
    return false;
  }

  // 不能是危险关键字
  if (DANGEROUS_KEYS.includes(appCode.toLowerCase())) {
    return false;
  }

  return true;
}

/**
 * 验证 clusterName 的安全性（专门为集群名称验证）
 * @param {string} clusterName - 集群名称
 * @returns {boolean} 是否安全
 */
export function validateClusterName(clusterName) {
  if (typeof clusterName !== 'string' || !clusterName) {
    return false;
  }

  // 长度限制（K8s 集群名称通常更长）
  // if (clusterName.length > 128) {
  //   return false;
  // }

  // // 只允许字母、数字、下划线、短横线、点号（符合 K8s 命名规范）
  // if (!/^[a-zA-Z0-9._-]+$/.test(clusterName)) {
  //   return false;
  // }

  // 不能是危险关键字
  if (DANGEROUS_KEYS.includes(clusterName.toLowerCase())) {
    return false;
  }

  // 不能以点号或短横线开头或结尾
  // if (/^[.-]|[.-]$/.test(clusterName)) {
  //   return false;
  // }

  return true;
}

export default {
  isSafeKey,
  createSafeObject,
  safeSet,
  safeGet,
  safeHas,
  safeDelete,
  toSafeObject,
  validateAppCode,
  validateClusterName,
};
