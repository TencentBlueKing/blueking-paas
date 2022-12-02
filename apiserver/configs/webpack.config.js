/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 *     http://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under
 * the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied. See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * We undertake not to change the open source license (MIT license) applicable
 * to the current version of the project delivered to anyone in the future.
 */
var path = require('path');
const glob = require('glob');
var webpack = require('webpack');
var BundleTracker = require('webpack-bundle-tracker');
const { VueLoaderPlugin } = require('vue-loader')
var utils = require('./utils')

var ROOT_PATH = path.resolve(__dirname, '..');
console.log(`ROOT_PATH: ${ROOT_PATH}`)


function resolve (dir) {
    return path.join(__dirname, '..', dir)
}

// Extract Sass to single file
const ExtractTextPlugin = require('extract-text-webpack-plugin');
const extractCss = new ExtractTextPlugin('[name]-css.css');
const extractSass = new ExtractTextPlugin('[name]-sass.css');

// Minimal css
const OptimizeCssAssetsPlugin = require('optimize-css-assets-webpack-plugin');

// Options for vue loader
const vueLoaderConfig = {
  loaders: utils.cssLoaders({
    sourceMap: true,
    extract: false
  })
}

// 默认入口
const defaultEntries = ["@babel/polyfill", './index.js'];
let autoEntriesCount = 0;

// 自动生成 entries
function generateEntries() {
  const autoEntries = {};
  const autoEntriesMap = {};

  function generateAutoEntries(path, prefix = '.') {
    // 使用 main.js 作为模块入口
    console.log(`generateAutoEntries: ${path}`)
    const chunkPath = path.replace(/\/main\.js$/, '');
    const chunkName = chunkPath.replace(/\//g, '.');
    autoEntriesMap[chunkName] = `${prefix}/${path}`;
  }

  glob.sync('**/main.js', {
    cwd: path.join(ROOT_PATH, 'paasng/assets/javascripts/'),
  }).forEach(path => generateAutoEntries(path, ));

  const autoEntryKeys = Object.keys(autoEntriesMap);
  autoEntriesCount = autoEntryKeys.length;
  // 生成 autoEntries
  autoEntryKeys.forEach(entryKey => {
    const entryPaths = [autoEntriesMap[entryKey]];

    // 只保留最外层的 entrypoint
    const segments = entryKey.split('.');
    while (segments.pop()) {
      const ancestor = segments.join('.');
      if (autoEntryKeys.includes(ancestor)) {
        entryPaths.unshift(autoEntriesMap[ancestor]);
      }
    }

    autoEntries[entryKey] = entryPaths
  })

  const manualEntries = {
    default: defaultEntries
  }

  return Object.assign(manualEntries, autoEntries);
}

let entries = generateEntries()
console.log(entries)

module.exports = {
  mode: 'production',
  context: path.join(ROOT_PATH, 'paasng/assets/javascripts'),
  entry: entries,
  output: {
    path: path.join(ROOT_PATH, 'paasng/public/assets/bundles/'),
    filename: '[name]-[chunkhash:8].bundle.js.js',
    chunkFilename: '[name].[chunkhash:8].chunk.js'
  },
  plugins: [
    new BundleTracker({
      filename: './paasng/public/webpack-stats.json'
    }),
    new webpack.ProvidePlugin({
      $: 'jquery',
      jQuery: 'jquery',
      'window.jQuery': 'jquery'
    }),
    extractCss,
    extractSass,
    new VueLoaderPlugin()
    // // node_modules 的依赖独立打包
    // new webpack.optimize.CommonsChunkPlugin({
    //   name: 'vendor', 
    //   minChunks: function(module){
    //     return module.context && module.context.includes('node_modules');
    //   }
    // }),
    // new webpack.optimize.UglifyJsPlugin({
    //   sourceMap: true,
    //   mangle: true,
    //   compress: {
    //     warnings: false, // Suppress uglification warnings
    //     pure_getters: true,
    //     unsafe: true,
    //     unsafe_comps: true,
    //     screw_ie8: true
    //   },
    //   output: {
    //     comments: false
    //   },
    //   exclude: [/\.min\.js$/gi] // skip pre-minified libs
    // }),
    // new OptimizeCssAssetsPlugin({
    //   assetNameRegExp: /\.css$/,
    //   cssProcessor: require('cssnano'),
    //   cssProcessorOptions: { discardComments: { removeAll: true } }
    // })
  ],
  optimization: {
    splitChunks: {
      cacheGroups: {
          commons: {
              test: /[\\/]node_modules[\\/]/,
              name: "vendors",
              chunks: "all"
          }
      }
    }
  },
  module: {
    rules: [
      { test: /bootstrap\/js\//, loader: 'imports-loader?jQuery=jquery' },
      { test: /bootstrap-table\/js\//, loader: 'imports-loader?jQuery=jquery' },
      {
        test: /\.vue$/,
        use: [
            {
                loader: 'thread-loader'
            },
            {
                loader: 'vue-loader',
                options: vueLoaderConfig
            }
        ]
      },
      // JavaScript
      {
        test: /\.js$/,
        exclude: /node_modules/,
        include: [resolve('paasng/assets/javascripts')],
        use: [
            {
              loader: 'thread-loader'
            },
            {
                loader: 'babel-loader',
                options: {
                  presets: [
                    [
                      "@babel/preset-env",
                      {
                        // "useBuiltIns": "entry"
                      }
                    ]
                  ],
                  plugins: [
                    ["babel-plugin-import-bk-magic-vue", {
                        "baseLibName": "bk-magic-vue"
                    }]
                  ]
                }
            }
        ]
      },
      // CSS
      {
        test: /\.css$/,
        use: extractCss.extract([ 'css-loader', 'postcss-loader' ])
      },
      // SASS
      {
        test: /\.sass$/,
        use: extractSass.extract({
          use: [
            { loader: 'css-loader' },
            { loader: 'sass-loader' }
          ],
          fallback: 'style-loader'
        })
      },
      {
        test: /\.scss$/,
        use: extractSass.extract({
          use: [
            { loader: 'css-loader' },
            { loader: 'sass-loader' }
          ],
          fallback: 'style-loader'
        })
      },
      // Fonts for Bootstrap
      {
        test: /\.(woff2?)$/,
        use: [
          {
            loader: 'url-loader',
            options: {
              limit: 1024 * 8
            }
          }
        ]
      },
      {
        test: /\.(ttf|eot)$/,
        loader: 'file-loader'
      },
      {
        test: /\.(jpe?g|png|gif|svg)$/i,
        use: [
          {
            loader: 'file-loader',
            options: {
              query: {
                name:'assets/[name].[ext]'
              }
            }
          }]
      },
    ]
  },

  resolve: {
    extensions: ['.js', '.vue', '.json'],
    alias: {
      'vue$': 'vue/dist/vue.esm.js',
      'Lib': path.join(ROOT_PATH, 'paasng/assets/javascripts'),
      'Styles': path.join(ROOT_PATH, 'paasng/assets/stylesheets'),
      'Extension': path.join(ROOT_PATH, 'node_modules/'),
      'BkMagicVue': path.join(ROOT_PATH, 'node_modules', process.env.EDITION.toUpperCase() === 'TE'? '@tencent/bk-magic-vue' : 'bk-magic-vue'),
      '@tencent': path.join(ROOT_PATH, 'node_modules/@tencent'),
    }
  }
};
