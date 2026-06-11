/**
 * 判断导航失败是否为可忽略的类型（重复导航或重定向导航）。
 *   1. 通过 error.name 直接判断
 *   2. 通过 Router.isNavigationFailure 静态方法判断
 *
 * @param {Object} Router - vue-router 构造函数
 * @param {Error|null} error - 导航过程中抛出的错误对象
 * @returns {boolean} 是否是可忽略的导航失败
 */
const isIgnoredNavigationFailure = (Router, error) => (
  error
  && (
    error.name === 'NavigationDuplicated'
    || error.name === 'NavigationRedirected'
    || (Router.isNavigationFailure
      && Router.NavigationFailureType
      && Router.isNavigationFailure(error, Router.NavigationFailureType.duplicated))
    || (Router.isNavigationFailure
      && Router.NavigationFailureType
      && Router.isNavigationFailure(error, Router.NavigationFailureType.redirected))
  )
);

/**
 * 包装路由导航方法（push/replace），
 * 使其在传入回调时保持原有调用方式，
 * 在返回 Promise 时静默吞掉可忽略的导航失败异常。
 *
 * @param {Object} Router - vue-router 构造函数
 * @param {Function} fn - 原始导航方法（push 或 replace）
 * @returns {Function} 包装后的导航方法
 */
const wrapNavigationMethod = (Router, fn) => function navigation(location, onResolve, onReject) {
  // 传统回调风格：用户传入了 onResolve/onReject，直接透传原始方法
  if (onResolve || onReject) {
    return fn.call(this, location, onResolve, onReject);
  }
  // Promise 风格：捕获可忽略的失败，避免未捕获的 Promise 异常
  const navigationResult = fn.call(this, location);
  if (!navigationResult || typeof navigationResult.catch !== 'function') {
    return navigationResult;
  }
  return navigationResult.catch((error) => {
    if (isIgnoredNavigationFailure(Router, error)) {
      return error;
    }
    return Promise.reject(error);
  });
};

/**
 * 安装导航兼容补丁，覆盖 Router.prototype 上的 push 和 replace 方法，
 *
 * @param {Object} Router - vue-router 构造函数
 */
export function installNavigationCompat(Router) {
  const { prototype } = Router;
  // 避免重复安装
  if (prototype.navigationCompatInstalled) {
    return;
  }
  prototype.push = wrapNavigationMethod(Router, prototype.push);
  prototype.replace = wrapNavigationMethod(Router, prototype.replace);
  prototype.navigationCompatInstalled = true;
}
