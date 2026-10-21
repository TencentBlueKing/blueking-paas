/**
 * 反代地址要和当前页面同源，否则响应里的 `frame-ancestors 'self'` 会拦住。接口按它自己看到的
 * Host 签发绝对地址，本地页面在另一台主机上时只留路径，请求仍走页面上的 `/api-svc` 代理。
 *
 * `direct` 为 true 时是沙箱暴露的主机，原样当作 iframe src。
 */
export const previewFrameUrl = (origin: string, direct: boolean, pageOrigin: string): string => {
  if (!origin) {
    return '';
  }

  if (direct) {
    return origin;
  }

  let url: URL;
  try {
    url = new URL(origin, pageOrigin);
  } catch {
    return origin;
  }

  if (url.origin === pageOrigin) {
    return url.href;
  }

  return `${pageOrigin}${url.pathname}${url.search}${url.hash}`;
};
