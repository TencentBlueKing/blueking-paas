module.exports = {
  host: process.env.BK_APP_HOST,
  port: 5000,
  publicPath: process.env.BK_STATIC_URL,
  cache: true,
  open: true,
  replaceStatic: true,

  // webpack config 配置
  configureWebpack() {
    return {
      devServer: {
      },
    };
  },

  chainWebpack(config) {
    config.module
      .rule('sass-loader')
      .test(/\.scss$/);
  },
};
