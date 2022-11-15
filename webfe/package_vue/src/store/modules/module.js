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

/*
    创建模块
*/
import http from '@/api';

export default {
  namespaced: true,
  state: {},
  getters: {},
  mutations: {},
  actions: {
    /**
         * 获取代码库类型
         */
    getCodeTypes ({ commit, state }, config = {}) {
      const url = `${BACKEND_URL}/api/sourcectl/providers/`;
      return http.get(url, config);
    },

    getModuleCodeTypes ({ commit, state }, { appCode, moduleId }, config = {}) {
      const url = `${BACKEND_URL}/api/sourcectl/applications/${appCode}/modules/${moduleId}/providers/`;
      return http.get(url, config);
    },

    /**
         * 获取支持的语言信息
         */
    getLanguageInfo ({ commit, state }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/regions/specs`;
      return http.get(url, config);
    },

    /**
         * 创建应用模块
         */
    createAppModule ({ commit, state }, { appCode, data }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/`;
      return http.post(url, data, config);
    },

    /**
         * 获取模块基本信息
         */
    getModuleBasicInfo ({ commit, state }, { appCode, modelName }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${modelName}`;
      return http.get(url, config);
    },

    /**
         * 删除模块
         */
    deleteModule ({ commit, state }, { appCode, moduleName }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleName}/`;
      return http.delete(url, config);
    },

    /**
         * 切换源码库
         */
    switchRepo ({ commit, state }, { appCode, modelName, data }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${modelName}/sourcectl/repo/modify/`;
      return http.post(url, data, config);
    },

    /**
         * 设置主模块
         */
    setMainModule ({ commit, state }, { appCode, modelName }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${modelName}/set_default/`;
      return http.post(url, {}, config);
    },

    /**
         * 设置部署限制
         */
    setDeployLimit ({ commit, state }, { appCode, modelName, params }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${modelName}/env_protection/`;
      return http.post(url, params, config);
    },

    /**
         * 获取环境保护
         */
    getEnvProtection ({ commit, state }, { appCode, modelName }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${modelName}/env_protection/?operation=deploy`;
      return http.get(url, {}, config);
    },

    /**
         * 获取应用模块域名信息
         */
    getModuleDomainInfo ({ commit, state }, { appCode }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/custom_domain_entrance/`;
      return http.get(url, {}, config);
    }
  }
};
