const webpack = require('webpack');
const path = require('path');
const fs = require('fs');
const dotenv = require('dotenv');
const dotenv_expand = require('dotenv-expand');

const PreTaskPlugin = require('./pre-task-plugin');

const now = new Date();
const RELEASE_VERSION = [now.getFullYear(), '-', (now.getMonth() + 1), '-', now.getDate(), '_', now.getHours(), ':', now.getMinutes(), ':', now.getSeconds()].join(''); // 版本号，eg: 2019-2-25_9:12:52

module.exports = {
  host: process.env.BK_APP_HOST,  // bk-local中配置
  port: 6060, // 端口号
  publicPath: '/',
  cache: true,
  open: true,
  replaceStatic: true,

  // webpack config 配置
  configureWebpack(context) {
    // bk-cli-service-webpack 在执行 build 命令时强制指定了 mode="production" 会导致开启太多代码优化, 无法很好排查问题(混淆了代码)
    // 因此需要设置另外的环境变量来覆盖这个行为
    if (process.env.BK_NODE_ENV === 'staging') {
      process.env.NODE_ENV = process.env.BK_NODE_ENV;
      // 由于目前是先读取 dotenv 再加载 bk.config.js, 因此执行 npm run build 时加载的仍然是 .bk.production.env 的变量
      context.mode = 'development';
    }
    
    return {
      // dev配置项
      devServer: {
        https: process.env.BK_HTTPS !== undefined,
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

    if (process.env.NODE_ENV === 'staging') {
      config.devtool('inline-source-map')
    }

    return config;
  },
};
