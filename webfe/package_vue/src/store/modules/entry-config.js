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

/**
 * 访问配置相关API
 */
import http from '@/api';

export default {
  namespaced: true,
  state: {},
  mutations: {},
  actions: {
    /**
         * 获取应用进程服务
         * @param {Object} params 包括appCode, env
         */
    getProcessServices({}, { appCode, moduleId, env }) {
      const url = `${BACKEND_URL}/svc_workloads/api/services/applications/${appCode}/modules/${moduleId}/envs/${env}/process_services/`;
      return http.get(url);
    },

    /**
         * 修改进程服务的端口列表
         * @param {Object} params 包括appCode, env, serviceName
         */
    updateServicePorts({}, { appCode, moduleId, env, serviceName, ports }) {
      const url = `${BACKEND_URL}/svc_workloads/api/services/applications/${appCode}/modules/${moduleId}/envs/${env}/process_services/${serviceName}`;
      return http.post(url, { ports });
    },

    /**
         * 修改模块主入口
         * @param {Object} params 包括appCode, env, serviceName, servicePortName
         */
    setServiceMainEntry({}, { appCode, moduleId, env, serviceName, servicePortName }) {
      const url = `${BACKEND_URL}/svc_workloads/api/services/applications/${appCode}/modules/${moduleId}/envs/${env}/process_ingresses/default`;
      return http.post(url, {
        service_name: serviceName,
        service_port_name: servicePortName,
      });
    },

    /**
         * 更新访问地址类型
         * @param {Object} params 包括appCode，moduleId, type
         */
    updateEntryType({}, { appCode, moduleId, type }) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/exposed_url_type/`;
      return http.put(url, {
        exposed_url_type: type,
      });
    },

    /**
         * 获取访问入口配置信息
         * @param {Object} params 包括appCode，moduleId
         */
    getEntryInfo({}, { appCode, moduleId }) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/default_entrance/`;
      return http.get(url);
    },

    /**
         * 添加域名
         * @param {Object} params
         */
    addDomainInfo({}, { appCode, data }) {
      const url = `${BACKEND_URL}/svc_workloads/api/services/applications/${appCode}/domains/`;
      return http.post(url, data);
    },

    /**
         *更新域名
         * @param {Object} params
         */
    updateDomainInfo({}, { appCode, data }) {
      const url = `${BACKEND_URL}/svc_workloads/api/services/applications/${appCode}/domains/${data.id}/`;
      return http.put(url, data);
    },

    /**
         * 获取默认根域名
         * @param {Object} params
         */
    getDefaultDomainInfo({}, { appCode, moduleId }) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/root_domains/`;
      return http.get(url);
    },

    /**
         * 修改默认根域名
         * @param {Object} params
         */
    updateRootDomain({}, { appCode, moduleId, data }) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/preferred_root_domain/`;
      return http.put(url, data);
    },

    /**
     * 获取访问入口列表数据
     * @param {Object} params 包括appCode，moduleId
     */
    getEntryDataList({}, { appCode }) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/entrance/`;
      return http.get(url);
    },
  },
};
