
const mockServer = require('./mock-server');
const containerBuild = process.env.APP_SPARK_CONTAINER_BUILD === '1';
const stripApiSvcPrefix = process.env.BK_API_PROXY_STRIP_PREFIX === '1';

/**
 * 预览响应里的绝对地址按 API 主机签发。本地页面是另一台主机，iframe 跟着跳过去就会被
 * `frame-ancestors 'self'` 拦住。把这些地址改回「发起这次代理的页面主机」，路径不动。
 */
const rewriteApiHost = (value, apiUrl, pageOrigin) => {
  if (!value || !apiUrl || !pageOrigin) return value;
  let api;
  try {
    api = new URL(apiUrl);
  } catch {
    return value;
  }
  return String(value)
    .split(api.origin).join(pageOrigin)
    .split(`http://${api.host}`).join(pageOrigin)
    .split(`https://${api.host}`).join(pageOrigin);
};

const keepPreviewOnPageHost = (proxyRes, req) => {
  const host = req.headers.host;
  if (!host) return;
  const forwarded = req.headers['x-forwarded-proto'];
  const proto = (Array.isArray(forwarded) ? forwarded[0] : forwarded) || 'http';
  const pageOrigin = `${proto}://${host}`;
  const apiUrl = process.env.BK_API_URL;
  ['location', 'content-security-policy'].forEach((name) => {
    const current = proxyRes.headers[name];
    if (!current) return;
    proxyRes.headers[name] = Array.isArray(current)
      ? current.map(item => rewriteApiHost(item, apiUrl, pageOrigin))
      : rewriteApiHost(current, apiUrl, pageOrigin);
  });
};

module.exports = {
  host: process.env.BK_APP_HOST,
  port: process.env.BK_APP_PORT,
  // 尾部斜杠保证 history 深层页面的懒加载 chunk 仍使用绝对资源路径。
  publicPath: containerBuild ? '__APP_SPARK_RT_BK_SITE_URL__/' : process.env.BK_STATIC_URL,
  cache: true,
  open: true,
  replaceStatic: !containerBuild,
  customEnv: containerBuild ? 'docker/container.env' : '',

  // webpack config 配置
  configureWebpack() {
    return {
      // 容器直接提供静态资源，不发布源码映射。
      ...(containerBuild ? { devtool: false } : {}),
      devServer: {
        setupMiddlewares: mockServer,
        proxy: [
          {
            context: ['/api-svc'],
            target: process.env.BK_API_URL,
            changeOrigin: true,
            secure: true,
            cookieDomainRewrite: '',
            ...(stripApiSvcPrefix ? { pathRewrite: { '^/api-svc': '' } } : {}),
            timeout: 0,
            proxyTimeout: 0,
            onProxyRes: keepPreviewOnPageHost,
          },
          {
            context: ['/agent'],
            target: 'http://127.0.0.1:5174',
            changeOrigin: true,
            timeout: 0,
            proxyTimeout: 0,
          },
        ].filter(item => item.target),
      },
    };
  },
};
