/** 同源 API 地址：origin + SITE_URL + 业务 path，避免调用方二次拼接站点前缀 */
export const resolveApiUrl = (path: string) => {
  if (/^https?:\/\//.test(path)) return path;
  const site = String(window.SITE_URL || '').replace(/\/$/, '');
  const ajax = String(process.env.BK_AJAX_URL_PREFIX || '').replace(/\/$/, '');
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return `${location.origin}${site}${ajax}${normalized}`;
};
