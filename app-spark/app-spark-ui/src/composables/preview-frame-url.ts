/** API 反代把应用挂在这段路径下。远程沙箱暴露出来的主机没有它。 */
const API_PREVIEW_PATH = '/preview/app/';

/**
 * 路径仍是 API 的 /preview/app/ 时，折回当前页面，请求继续走页面上的代理。
 * 暴露出来的预览主机原样当作 iframe src。
 */
export const previewFrameUrl = (origin: string, pageOrigin: string): string => {
  if (!origin) {
    return '';
  }

  let url: URL;
  try {
    url = new URL(origin, pageOrigin);
  } catch {
    return origin;
  }

  if (!url.pathname.includes(API_PREVIEW_PATH)) {
    return url.href;
  }

  if (url.origin === pageOrigin) {
    return url.href;
  }

  return `${pageOrigin}${url.pathname}${url.search}${url.hash}`;
};
