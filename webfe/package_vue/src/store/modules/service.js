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
    增强服务模块
*/
import http from '@/api';

export default {
  namespaced: true,
  state: {},
  getters: {},
  mutations: {},
  actions: {
    /**
     * 启用增强服务
     */
    enableServices({}, params, config = {}) {
      const url = `${BACKEND_URL}/api/services/service-attachments/`;
      return http.post(url, params, config);
    },

    /**
     * 获取某服务可被共享的模块
     */
    getServicesShareableModule({}, { appCode, moduleId, serviceId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/services/${serviceId}/shareable_modules/`;
      return http.get(url, config);
    },

    /**
     * 创建增强服务共享关系
     */
    createSharedAttachment({}, params, config = {}) {
      const requestParams = Object.assign({}, params);
      const { appCode, moduleId, serviceId } = requestParams;
      delete requestParams.appCode;
      delete requestParams.moduleId;
      delete requestParams.serviceId;
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/services/${serviceId}/shared_attachment`;
      return http.post(url, requestParams, config);
    },

    /**
     * 解除共享关系
     */
    deleteSharedAttachment({}, { appCode, moduleId, serviceId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/services/${serviceId}/shared_attachment`;
      return http.delete(url, config);
    },

    /**
     * 查看模块增强服务被共享引用情况
     */
    getServicesShareDetail({}, { appCode, moduleId, serviceId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/services/${serviceId}/sharing_references/related_modules/`;
      return http.get(url, config);
    },

    /**
     * 查看已创建的共享关系
     */
    getSharedAttachmentDetail({}, { appCode, moduleId, serviceId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/services/${serviceId}/shared_attachment`;
      return http.get(url, config);
    },

    /**
     * 获取增强服务列表
     */
    getServicesList({}, { appCode, moduleId }, config = {}) {
      // /backend/api/bkapps/applications/nsu230327/modules/dev/services'
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/services/`;
      return http.get(url, config);
    },

    /**
     * 获取增强服务环境变量信息
     */
    getCredentialsEnabled({}, { appCode, moduleId, service }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/services/${service}/credentials_enabled/`;
      return http.get(url, config);
    },

    /**
     * 更新增强服务环境变量信息
     */
    updateCredentialsEnabled({}, { appCode, moduleId, service, data }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/services/${service}/credentials_enabled/`;
      return http.put(url, data, config);
    },

    /**
     * 删除/停用增强服务
     */
    deleteService({}, { appCode, moduleId, service }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/services/${service}/`;
      return http.delete(url, {}, config);
    },

    /**
     * 获取服务详情
     */
    getServiceDetail({}, { service }, config = {}) {
      const url = `${BACKEND_URL}/api/services/${service}/`;
      return http.get(url, {}, config);
    },

    /**
     * 获取增强服务详情列表
     */
    getServiceInstances({}, { appCode, moduleId, service }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/services/${service}/`;
      return http.get(url, {}, config);
    },

    /**
     * 获取应用增强服务信息
     */
    getServiceInfo({}, { appCode, moduleId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/services/info/`;
      return http.get(url, {}, config);
    },

    /**
     * 获取应用模块绑定服务时，可能的详情方案
     */
    getServicePossiblePlans({}, { appCode, moduleId, service }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/services/${service}/possible_plans`;
      return http.get(url, {}, config);
    },

    /**
     * 查询模块的已解绑增强服务
     */
    getServicesUnboundAttachments({}, { appCode, moduleId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/services/unbound_attachments/`;
      return http.get(url, {}, config);
    },

    /**
     * 手动回收已解绑实例
     */
    recyclingService({}, { appCode, moduleId, serviceId, instanceId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/services/${serviceId}/unbound_attachments/?instance_id=${instanceId}`;
      return http.delete(url, {}, config);
    },

    /**
     * 查询解绑实例敏感字段
     */
    queryUnbindInstanceSensitiveFields({}, { appCode, moduleId, serviceId, data }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/services/${serviceId}/unbound_attachments/retrieve_field/`;
      return http.post(url, data, config);
    },
  },
};
