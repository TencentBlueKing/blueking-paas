import type { IFetchConfig } from './index';
import Message from '@/common/message';
import { loginModal, redirectToLogin } from '@/common/auth';

// 请求执行失败拦截器
export default (error: any, config: IFetchConfig) => {
  const {
    code,
    message,
    response,
  } = error;
  const authenticationRequired = code === 401 || code === 'AUTHENTICATION_REQUIRED';
  // 用户登录状态失效。新协议把稳定业务码放在 body.code，不能只判断 HTTP 数字状态。
  if (authenticationRequired) {
    if (response?.login_url) {
      redirectToLogin(response.login_url);
    } else {
      loginModal();
    }
  }
  // 全局捕获错误给出提示
  if (config.globalError && !authenticationRequired) {
    Message({ theme: 'error', message });
  }
  return Promise.reject(error);
};
