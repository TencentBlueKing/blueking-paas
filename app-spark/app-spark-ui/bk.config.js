
const mockServer = require('./mock-server');

module.exports = {
  host: process.env.BK_APP_HOST,
  port: process.env.BK_APP_PORT,
  publicPath: process.env.BK_STATIC_URL,
  cache: true,
  open: true,
  replaceStatic: true,

  // webpack config 配置
  configureWebpack() {
    return {
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
