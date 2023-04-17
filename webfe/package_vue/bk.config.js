const webpack = require('webpack');
const HtmlWebpackPlugin = require('html-webpack-plugin')

const PreTaskPlugin = require('./pre-task-plugin');

const now = new Date()
// const RELEASE_VERSION = [now.getFullYear(), ]

module.exports = {
  host: process.env.BK_APP_HOST,
  port: 6060,
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
    // plugin
    config
      .plugin('providePlugin')
      .use(new webpack.ProvidePlugin, [{
        $: 'jquery',
      }]);
      config
      .plugin('htmlWebpackPlugin')
      .use(new HtmlWebpackPlugin, [{
        RELEASE_VERSION: RELEASE_VERSION,
      }]);
    config.plugin('preTaskPlugin')
      .use(new PreTaskPlugin());
    return config;
  },
};
