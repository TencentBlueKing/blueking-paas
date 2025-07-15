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

const path = require('path');
const fs = require('fs');

const APP_VERSION = process.env.BK_APP_VERSION || 'ee';

const JSON_DIR_PATH = path.resolve(__dirname, './static/json');
const JS_DIR_PATH = path.resolve(__dirname, './static/js');
// const RUNTIME_DIR_PATH = path.resolve(__dirname, './static/runtime');

class PreTaskPlugin {
  constructor() {
    console.log('APP_VERSION', APP_VERSION);
    console.log('NODE_ENV', process.env.NODE_ENV);
    console.time('Pre task');
    const paasStaticPath = path.resolve(JSON_DIR_PATH, './paas_static.js');
    const bklogoutPath = path.resolve(JS_DIR_PATH, './bklogout.js');
    // const runtimePath = path.resolve(RUNTIME_DIR_PATH, './runtime.js');

    // 安全删除文件，避免 TOCTTOU 竞争条件
    try {
      fs.unlinkSync(paasStaticPath);
    } catch (err) {
      // 忽略文件不存在的错误
      if (err.code !== 'ENOENT') {
        throw err;
      }
    }

    try {
      fs.unlinkSync(bklogoutPath);
    } catch (err) {
      // 忽略文件不存在的错误
      if (err.code !== 'ENOENT') {
        throw err;
      }
    }

    // 复制 paas_static - 使用原子写入
    const PAASSTATIC = APP_VERSION === 'te' ? `../../webfe-settings/paas_static.${APP_VERSION}.js` : `../../static/json/paas_static.${APP_VERSION}.js`;
    const staticData = fs.readFileSync(path.resolve(JSON_DIR_PATH, PAASSTATIC));
    const tempStaticPath = `${paasStaticPath}.tmp`;
    fs.writeFileSync(tempStaticPath, staticData);
    fs.renameSync(tempStaticPath, paasStaticPath);

    // 复制runtime
    // const PAASRUNTIME = APP_VERSION === 'te' ?
    // `../../webfe-settings/runtime.${APP_VERSION}.js` : `../../static/runtime/runtime.${APP_VERSION}.js`;
    // const runtimeData = fs.readFileSync(path.resolve(RUNTIME_DIR_PATH, PAASRUNTIME));
    // let envs = {};
    // // let fileContent = runtimeData.toString();

    // if (process.env.NODE_ENV === 'production') {
    //   envs = Object.assign({}, {
    //     NODE_ENV: 'production',
    //   }, process.env);
    // } else {
    //   envs = Object.assign({}, {
    //     NODE_ENV: 'development',
    //   }, process.env);
    // }
    // for (const key in envs) {
    //   const reg = new RegExp(`<%=${key}%>`);
    //   fileContent = fileContent.replace(reg, JSON.stringify(envs[key]));
    // }

    // fileContent = fileContent.replace(/<%=[\w]+%>/g, '\'\'');
    // fs.writeFileSync(runtimePath, fileContent);

    // 复制 bklogout - 使用原子写入
    const PAASLOGOUT = APP_VERSION === 'te' ? `../../webfe-settings/bklogout.${APP_VERSION}.js` : `../../static/js/bklogout.${APP_VERSION}.js`;
    const logoutData = fs.readFileSync(path.resolve(JS_DIR_PATH, PAASLOGOUT));
    const tempLogoutPath = `${bklogoutPath}.tmp`;
    fs.writeFileSync(tempLogoutPath, logoutData);
    fs.renameSync(tempLogoutPath, bklogoutPath);
    console.timeEnd('Pre task');
  }

  apply(compiler) {
    compiler.hooks.done.tap('done', () => { });
  }
}

module.exports = PreTaskPlugin;
