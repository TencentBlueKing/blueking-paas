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
    进程相关数据
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
     * 获取进程下实例使用资源数据
     * @param {Object} params 包括appCode, env
     */
    getInstanceMetrics({}, params, config = {}) {
      const { appCode, moduleId, env } = params;
      // const instanceName = params.instanceName
      delete params.appCode;
      delete params.moduleId;
      delete params.env;
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/envs/${env}/metrics/?${json2Query(params)}`;
      return http.get(url, config);
    },

    /**
     * 获取实例的webconsole信息
     * @param {Object} params 包括appCode instanceName env
     */
    getInstanceConsole({}, { appCode, moduleId, instanceName, env, processType }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/envs/${env}/processes/${processType}/instances/${instanceName}/webconsole/`;

      return http.get(url, config);
    },

    /**
     * 加载进程
     * @param {Object} params 包括appCode instanceName env
     */
    getProcesses({}, { appCode, moduleId, env }, config = {}) {
      const url = `${BACKEND_URL}/svc_workloads/api/processes/applications/${appCode}/modules/${moduleId}/envs/${env}/processes/list/`;
      return http.get(url, config);
    },

    /**
     * 加载最后一个版本的进程
     * @param {Object} params 包括appCode instanceName env releaseId
     */
    getLastVersionProcesses({}, { appCode, moduleId, env, releaseId }, config = {}) {
      const url = `${BACKEND_URL}/svc_workloads/api/processes/applications/${appCode}/modules/${moduleId}/envs/${env}/processes/list/?only_latest_version=true&release_id=${releaseId}`;
      return http.get(url, config);
    },

    /**
     * 更新进程
     * @param {Object} params 包括appCode instanceName env data
     */
    updateProcess({}, { appCode, moduleId, env, data }, config = {}) {
      const url = `${BACKEND_URL}/svc_workloads/api/processes/applications/${appCode}/modules/${moduleId}/envs/${env}/processes/`;
      return http.post(url, data, config);
    },

    /**
     * 加载实例日志数据
     * @param {Object} params 包括appCode instanceName env
     */
    getInstanceLog({}, { appCode, moduleId, data }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/log/stdout/list/?time_range=5m`;
      return http.post(url, data, config);
    },

    /**
     * 获取进程服务数据
     * @param {Object} params tplType模版类型, region应用版本 tplName模版名称
     */
    getProcessService({}, { appCode, moduleId, env }, config = {}) {
      const url = `${BACKEND_URL}/svc_workloads/api/services/applications/${appCode}/modules/${moduleId}/envs/${env}/process_services/`;
      return http.get(url, config);
    },
  },
};
