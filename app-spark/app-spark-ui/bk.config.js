
const mockServer = require('./mock-server');
const containerBuild = process.env.APP_SPARK_CONTAINER_BUILD === '1';

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
            timeout: 0,
            proxyTimeout: 0,
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
