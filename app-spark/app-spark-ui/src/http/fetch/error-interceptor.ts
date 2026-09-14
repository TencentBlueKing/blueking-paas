import type { IFetchConfig } from './index';
import { Message } from 'bkui-vue';
import { loginModal, redirectToLogin } from '@/common/auth';

// 请求执行失败拦截器
export default (error: any, config: IFetchConfig) => {
  const {
    code,
    message,
    response,
  } = error;
  switch (code) {
    // 用户登录状态失效
    case 401:
      if (response?.login_url) {
        redirectToLogin(response.login_url);
      } else {
        loginModal();
      }
      break;
  }
  // 全局捕获错误给出提示
  if (config.globalError && code !== 401) {
    Message({ theme: 'error', message });
  }
  return Promise.reject(error);
};
