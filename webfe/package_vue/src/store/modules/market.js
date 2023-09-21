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

/*
    应用市场相关数据
*/
import http from '@/api';

export default {
  namespaced: true,
  state: {},
  getters: {},
  mutations: {},
  actions: {
    /**
         * 上传应用logo
         *
         * @param {Object} params 包括appCode, 文件数据
         * @param {Object} config ajax配置
         */
    uploadAppLogo({}, { appCode, data }, config) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/logo/`;
      return http.put(url, data, config);
    },

    /**
         * 获取应用的所有信息
         *
         * @param {String} appCode 应用id
         * @param {Object} config ajax配置
         */
    getAppBaseInfo({}, appCode, config) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/`;
      return http.get(url, config);
    },

    /**
         * 获取应用对应环境部署信息
         *
         * @param {Object} params 包括appCode, env
         * @param {Object} config ajax配置
         */
    getAppEnvInfo({}, { appCode, env }, config) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/envs/${env}/released_state/`;
      return http.get(url, config);
    },

    /**
         * 获取应用市场信息
         *
         * @param {String} appCode 应用id
         * @param {Object} config ajax配置
         */
    getAppMarketInfo({}, appCode, config) {
      const url = `${BACKEND_URL}/api/market/products/${appCode}/`;
      return http.get(url, config);
    },

    /**
         * 获取分类列表
         */
    getTags({}, config) {
      const url = `${BACKEND_URL}/api/market/tags`;
      return http.get(url, config);
    },

    /**
         * 获取业务列表
         */
    getBusinessList({}, config) {
      const url = `${BACKEND_URL}/api/market/corp_products/`;
      return http.get(url, config);
    },

    /**
         * 注册应用市场信息
         *
         * @param {Object} params 参数
         * @param {Object} config ajax配置
         */
    registerMarketInfo({}, params, config) {
      const url = `${BACKEND_URL}/api/market/products/`;
      return http.post(url, params, config);
    },

    /**
         * 更新应用市场信息
         *
         * @param {Object} params 参数，包括appCode, data
         * @param {Object} config ajax配置
         */
    updateMarketInfo({}, { appCode, data }, config) {
      const url = `${BACKEND_URL}/api/market/products/${appCode}`;
      return http.put(url, data, config);
    },

    /**
         * 获取应用市场配置
         *
         * @param {String} appCode 应用id
         * @param {Object} config ajax配置
         */
    getAppMarketConfig({}, appCode, config) {
      const url = `${BACKEND_URL}/api/market/applications/${appCode}/config/`;
      return http.get(url, config);
    },

    /**
         * 修改应用市场配置
         *
         * @param {Object} params 参数，包括appCode, data
         * @param {Object} config ajax配置
         */
    updateAppMarketConfig({}, { appCode, data }, config) {
      const url = `${BACKEND_URL}/api/market/applications/${appCode}/config/`;
      return http.put(url, data, config);
    },

    /**
         * 更新应用市场服务开关
         *
         * @param {Object} params 参数，包括appCode, data
         * @param {Object} config ajax配置
         */
    updateAppMarketSwitch({}, { appCode, data }, config) {
      const url = `${BACKEND_URL}/api/market/applications/${appCode}/switch/`;
      return http.post(url, data, config);
    },

    /**
         * 检查当前发布的准备条件是否已经满足
         *
         * @param {String} appCode 应用id
         * @param {Object} config ajax配置
         */
    getAppMarketPrepare({}, appCode, config) {
      const url = `${BACKEND_URL}/api/market/applications/${appCode}/publish/preparations/`;
      return http.get(url, config);
    },

    /**
         * 切换应用市场访问地址
         *
         * @param {String} params 请求参数
         * @param {Object} config ajax配置
         */
    updateAppMarketAvaliableAddress({ }, params, config) {
      const { source_url_type, source_tp_url, custom_domain_url, appCode } = params;
      const url = `${BACKEND_URL}/api/market/applications/${appCode}/config/`;
      return http.put(url, { source_url_type, source_tp_url, custom_domain_url }, config);
    },

    /**
         * 获取移动端应用市场信息
         *
         * @param {String} appCode 应用id
         * @param {Object} config ajax配置
         */
    getMobileMarketInfo({}, { appCode }, config) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/mobile_config/`;
      return http.get(url, config);
    },

    /**
         * 启用移动端应用市场
         *
         * @param {Object} params 参数，包括appCode, data
         * @param {Object} config ajax配置
         */
    enableMobileMarket({}, { appCode, env, data }, config) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/envs/${env}/mobile_config/on/`;
      return http.post(url, data, config);
    },

    /**
         * 停用移动端应用市场
         *
         * @param {Object} params 参数，包括appCode, data
         * @param {Object} config ajax配置
         */
    disableMobileMarket({}, { appCode, env }, config) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/envs/${env}/mobile_config/off/`;
      return http.post(url, {}, config);
    },

    /**
         * 描述应用开关功能
         *
         * @param {Object} params 参数，包括appCode
         * @param {Object} config ajax配置
         */
    getDescAppStatus({}, appCode, config) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/protections/`;
      return http.get(url, config);
    },

    /**
         * 修改描述应用状态
         *
         * @param {Object} params 参数，包括appCode
         * @param {Object} config ajax配置
         */
    changeDescAppStatus({}, appCode, config) {
      const url = `${BACKEND_URL}/api/bkapps/applications/feature_flags/${appCode}/switch/app_desc_flag/`;
      return http.put(url, {}, config);
    },

    /**
     * 获取插件分类列表
     *
     * @param {String} appCode 应用id
     * @param {Object} config ajax配置
     */
    getPluginTypeList({}, config) {
      const url = `${BACKEND_URL}/api/bk_plugin_tags/`;
      return http.get(url, config);
    },


    /**
     * 更新访问地址
     *  @param {String} appCode 应用id
     * @param {String} data 需要更新的数据
     * @param {Object} config ajax配置
     */
    updateMarketUrl({}, { appCode, data }, config) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/entrances/market/`;
      return http.post(url, data, config);
    },
  },
};
