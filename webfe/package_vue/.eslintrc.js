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

module.exports = {
    root: true,
    env: {
        browser: true,
    },
    // vue 相关的规则，加载 vue 规则会自动加载 es6 的规则
    // 如果不需要 vue 仅仅只是检测 es6 那么配置 @tencent/eslint-config-bk/index 即可
    extends: [
        '@tencent/eslint-config-bk/vue'
    ],
    // vue plugin，不需要自行安装 eslint-plugin-vue，安装 @tencent/eslint-config-bk 时会把 eslint 相关的包全部安装
    // 如果不需要 vue 仅仅只是检测 es6 那么这里可以不用配置 eslint-plugin-vue
    plugins: [
        'vue'
    ],
    // value 为 true 允许被重写，为 false 不允许被重写
    globals: {
        NODE_ENV: true,
        SITE_URL: true,
        BACKEND_URL: true,
        BK_SITE_URL: true,
        BK_BACKEND_URL: true,
        $: true
    },
    // 添加自定义的规则以及覆盖 @tencent/eslint-config-bk 里的规则
    // @tencent/eslint-config-bk 里所有的规则在这里
    rules: {
        // 覆盖 vue 规则
        // 'vue/no-dupe-keys': 'off',
        // 覆盖 es6 规则
        // 'no-unused-vars': 'off'
        // "vue/require-component-is": "error",
        "vue/require-prop-type": "off",
        semi:['error','always']
    },

    // vue/script-indent 规则只会检测 .vue 文件里的 script 而不会去检测 .js 文件，
    // 但是 eslint 默认的 indent 规则会检测 .js 文件和 .vue 文件，为了不让 vue/script-indent 和 indent 相互干扰，
    // 所以这里需要配置 overrides，让 eslint indent 的规则不用检测 .vue 文件
    overrides: [
        {
            files: ['*.vue'],
            rules: {
                indent: 'off',
                semi:['error','always']
            }
        }
    ]
};
