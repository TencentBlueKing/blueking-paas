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
    环境变量
*/
import http from '@/api';

export default {
  namespaced: true,
  state: {},
  getters: {},
  mutations: {},
  actions: {
    /**
         * 获取所有运行时基础镜像
         */
    getAllImages ({ commit, state }, { appCode, moduleId }) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/runtime/list/`;
      return http.get(url);
    },

    /**
         * 获取运行时基础信息
         */
    getRuntimeInfo ({ commit, state }, { appCode, moduleId }) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/runtime/`;
      return http.get(url);
    },

    /**
         * 保存运行时基础信息
         */
    updateRuntimeInfo ({ commit, state }, { appCode, moduleId, data }) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/runtime/`;
      return http.post(url, data);
    },

    /**
         * 从模块导入环境变量
         * @param {Object} params 包括appCode, moduleId, sourceModuleName
         */
    exportModuleEnv ({ commit, state }, { appCode, moduleId, sourceModuleName }) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/config_vars/clone_from/${sourceModuleName}`;
      return http.post(url, {});
    },

    /**
         * 应用基本信息
         */
    getBasicInfo ({ commit, state }, { appCode }) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/config_vars/builtin/app/`;
      return http.get(url);
    },

    /**
         * 应用运行时信息
         */
    getBkPlatformInfo ({ commit, state }, { appCode }) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/config_vars/builtin/bk_platform/`;
      return http.get(url);
    },

    /**
         * 蓝鲸体系内平台信息
         */
    getAppRuntimeInfo ({ commit, state }, { appCode }) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/config_vars/builtin/runtime/`;
      return http.get(url);
    }
  }
};
