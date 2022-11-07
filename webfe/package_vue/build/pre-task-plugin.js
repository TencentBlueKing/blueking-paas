/*
* Tencent is pleased to support the open source community by making
* 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
* Copyright (C) 2017-2022THL A29 Limited, a Tencent company.  All rights reserved.
* Licensed under the MIT License (the "License").
* You may not use this file except in compliance with the License.
* You may obtain a copy of the License at http://opensource.org/licenses/MIT
* Unless required by applicable law or agreed to in writing,
* software distributed under the License is distributed on
* an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
* either express or implied. See the License for the
* specific language governing permissions and limitations under the License.
*
* We undertake not to change the open source license (MIT license) applicable
*
* to the current version of the project delivered to anyone in the future.
*/

const path = require('path');
const fs = require('fs');
const config = require('../config');

const APP_VERSION = process.env.APP_VERSION || 'ee';

const JSON_DIR_PATH = path.resolve(__dirname, '../static/json');
const JS_DIR_PATH = path.resolve(__dirname, '../static/js');
const RUNTIME_DIR_PATH = path.resolve(__dirname, '../static/runtime');

class PreTaskPlugin {
    constructor () {
        console.time('Pre task');
        const paasStaticPath = path.resolve(JSON_DIR_PATH, './paas_static.js');
        const bklogoutPath = path.resolve(JS_DIR_PATH, './bklogout.js');
        const runtimePath = path.resolve(RUNTIME_DIR_PATH, './runtime.js');

        if (fs.existsSync(paasStaticPath)) {
            fs.unlinkSync(paasStaticPath);
        }

        if (fs.existsSync(bklogoutPath)) {
            fs.unlinkSync(bklogoutPath);
        }

        // 复制paas_static
        const PAASSTATIC = APP_VERSION === 'te' ? `../../webfe-settings/paas_static.${APP_VERSION}.js` : `./paas_static.${APP_VERSION}.js`;
        const staticData = fs.readFileSync(path.resolve(JSON_DIR_PATH, PAASSTATIC));
        fs.writeFileSync(paasStaticPath, staticData);

        // 复制runtime
        const PAASRUNTIME = APP_VERSION === 'te' ? `../../webfe-settings/runtime.${APP_VERSION}.js` : `./runtime.${APP_VERSION}.js`;
        const runtimeData = fs.readFileSync(path.resolve(RUNTIME_DIR_PATH, PAASRUNTIME));
        let envs = {};
        let fileContent = runtimeData.toString();

        if (process.env.NODE_ENV === 'production') {
            envs = Object.assign({}, config.build.env, process.env);
        } else {
            envs = Object.assign({}, config.dev.env, process.env);
        }
        for (const key in envs) {
            const reg = new RegExp(`<%=${key}%>`);
            fileContent = fileContent.replace(reg, JSON.stringify(envs[key]));
        }

        fileContent = fileContent.replace(/<%=[\w]+%>/g, "''");
        fs.writeFileSync(runtimePath, fileContent);

        // 复制bklogout
        const PAASLOGOUT = APP_VERSION === 'te' ? `../../webfe-settings/bklogout.${APP_VERSION}.js` : `./bklogout.${APP_VERSION}.js`;
        const logoutData = fs.readFileSync(path.resolve(JS_DIR_PATH, PAASLOGOUT));
        fs.writeFileSync(bklogoutPath, logoutData);
        console.timeEnd('Pre task');
    }

    apply (compiler) {
        compiler.plugin('done', function () { });
    }
}

module.exports = PreTaskPlugin;
