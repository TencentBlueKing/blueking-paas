import {
  showLoginModal,
} from '@blueking/login-modal';

interface ILoginData {
  loginUrl?: string
}
// 获取登录地址
const getLoginUrl = (url: string, cUrl: string, isFromLogout: boolean) => {
  const loginUrl = new URL(url);
  if (isFromLogout) {
    loginUrl.searchParams.append('is_from_logout', '1');
  }
  loginUrl.searchParams.append('c_url', cUrl);
  return loginUrl.href;
};

export const redirectToLogin = (loginUrl: string) => {
  try {
    const target = new URL(loginUrl, location.origin);
    if (!target.searchParams.get('c_url')) {
      target.searchParams.set('c_url', location.href);
    }
    location.href = target.href;
  } catch {
    location.href = loginUrl;
  }
};

// 跳转到登录页
export const login = (data: ILoginData = {}) => {
  if (data.loginUrl) {
    redirectToLogin(data.loginUrl);
    return;
  }
  location.href = getLoginUrl(process.env.BK_LOGIN_URL, location.origin, false);
};

// 打开登录弹框
export const loginModal = () => {
  const loginUrl = getLoginUrl(
    `${process.env.BK_LOGIN_URL}/plain`,
    `${location.origin + window.SITE_URL}/static/login_success.html`,
    false
  )
  showLoginModal({ loginUrl })
}

// 退出登录
export const logout = () => {
  location.href = getLoginUrl(process.env.BK_LOGIN_URL, location.origin, true);
};
