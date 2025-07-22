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
import { json2Query } from '@/common/tools';

export default {
  namespaced: true,
  state: {},
  getters: {},
  mutations: {},
  actions: {
    /**
     * 获取所有运行时基础镜像
     */
    getAllImages({}, { appCode, moduleId }) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/runtime/list/`;
      return http.get(url);
    },

    /**
     * 获取运行时基础信息
     */
    getRuntimeInfo({}, { appCode, moduleId }) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/runtime/`;
      return http.get(url);
    },

    /**
     * 保存运行时基础信息
     */
    updateRuntimeInfo({}, { appCode, moduleId, data }) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/runtime/`;
      return http.post(url, data);
    },

    /**
     * 从模块导入环境变量
     * @param {Object} params 包括appCode, moduleId, sourceModuleName
     */
    exportModuleEnv({}, { appCode, moduleId, sourceModuleName }) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/config_vars/clone_from/${sourceModuleName}`;
      return http.post(url, {});
    },

    /**
     * 应用基本信息
     */
    getBasicInfo({}, { appCode }) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/config_vars/builtin/app/`;
      return http.get(url);
    },

    /**
     * 应用运行时信息
     */
    getBkPlatformInfo({}, { appCode }) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/config_vars/builtin/bk_platform/`;
      return http.get(url);
    },

    /**
     * 蓝鲸体系内平台信息
     */
    getAppRuntimeInfo({}, { appCode }) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/config_vars/builtin/runtime/`;
      return http.get(url);
    },

    /**
     * 获取环境变量
     */
    getEnvVariables({}, { appCode, moduleId, orderBy }) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/config_vars/?order_by=${orderBy}`;
      return http.get(url);
    },

    /**
     * 获取有冲突的环境变量列表
     */
    getConflictedEnvVariables({}, { appCode, moduleId }) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/config_vars/conflicted_keys/`;
      return http.get(url);
    },

    /**
     * 保存环境变量数据
     */
    batchConfigVars({}, { appCode, moduleId, data }) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/config_vars/batch/`;
      return http.post(url, data);
    },

    /**
     * 新增单个环境变量
     */
    createdEnvVariable({}, { appCode, moduleId, data }) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/config_vars/`;
      return http.post(url, data);
    },

    /**
     * 修改单个环境变量
     */
    updateEnvVariable({}, { appCode, moduleId, varId, data }) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/config_vars/${varId}/`;
      return http.put(url, data);
    },

    /**
     * 删除单个环境变量
     */
    deleteEnvVariable({}, { appCode, moduleId, varId }) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/config_vars/${varId}/`;
      return http.delete(url, {});
    },

    /**
     * 获取预设环境变量
     */
    getConfigVarPreset({}, { appCode, moduleId, params }) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/config_vars/preset/?${json2Query(params)}`;
      return http.get(url, {});
    },
  },
};
