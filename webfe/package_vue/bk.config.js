const webpack = require('webpack');

const PreTaskPlugin = require('./pre-task-plugin');

const now = new Date();
const RELEASE_VERSION = [now.getFullYear(), '-', (now.getMonth() + 1), '-', now.getDate(), '_', now.getHours(), ':', now.getMinutes(), ':', now.getSeconds()].join(''); // 版本号，eg: 2019-2-25_9:12:52

module.exports = {
  host: process.env.BK_APP_HOST,
  port: 6060,
  publicPath: process.env.NODE_ENV === 'development' ? '/' : process.env.BK_PAAS3_URL,
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
    // plugin
    config
      .plugin('providePlugin')
      .use(webpack.ProvidePlugin, [{
        $: 'jquery',
      }]);
    config
      .plugin('html')
      .use(webpack.DefinePlugin, [{
        RELEASE_VERSION: JSON.stringify(RELEASE_VERSION),
      }]);
    config.plugin('preTaskPlugin')
      .use(new PreTaskPlugin());
    return config;
  },
};
