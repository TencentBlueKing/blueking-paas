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
    这里管理当前 app 所拥有的属性
*/
import Vue from 'vue';
import http from '@/api';

// store
const state = {
  appLinks: {},
  appCode: '',
};

// getters
const getters = {};

// mutations
const mutations = {
  updateAppExposedLinkUrl(state, { appCode, env, value }) {
    state.appLinks[appCode] = state.appLinks[appCode] || {};
    state.appLinks[appCode][env] = value;
  },
};

// actions
const actions = {
  async fetchAppExposedLinkUrl({ commit, state }, { appCode, env }) {
    return new Promise((resolve) => {
      Vue.http.get(`${BACKEND_URL}/api/bkapps/applications/${appCode}/envs/${env}/released_state/`).then(
        (resp) => {
          commit('updateAppExposedLinkUrl', {
            appCode,
            env,
            value: resp.exposed_link.url,
          });
          resolve(state.appLinks[appCode][env]);
        },
        () => {
          resolve(undefined);
        }
      );
    });
  },

  /**
   * 获取应用所有访问入口的ViewSet，访问入口包括: 由平台默认提供的地址(与模块环境 1v1 对应/由用户设置的独立域名地址(与模块环境存在 1vN 关系)
   *
   * @param {String} appCode 应用id
   * @param {Object} config ajax配置
   */
  getAppCustomDomainEntrance({}, appCode, config) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/custom_domain_entrance/`;
    return http.get(url, config);
  },

  /**
   * 获取应用指定模块初始化模块地址
   */
  getAppInitTemplateUrl({}, { appCode, moduleId }) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/sourcectl/init_template/`;
    return http.post(url, {});
  },

  /**
   * 获取应用默认初始化模块地址
   */
  getAppDefaultInitTemplateUrl({}, { appCode }) {
    const url = `${BACKEND_URL}/api/sourcectl/init_templates/${appCode}/ `;
    return http.post(url, {});
  },

  /**
   * 获取应用仪表盘数据
   */
  getBuiltinDashboards({}, { appCode }) {
    const url = `${BACKEND_URL}/api/monitor/applications/${appCode}/builtin_dashboards/`;
    return http.get(url);
  },

  /**
   * 获取应用模板信息
   */
  getAppTemplateInfo({}, { appCode, moduleId }) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/template/`;
    return http.get(url);
  },
};

export default {
  state,
  getters,
  mutations,
  actions,
};
