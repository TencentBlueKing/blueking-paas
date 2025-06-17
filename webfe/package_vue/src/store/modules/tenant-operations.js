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
 * 多租户-用户管理
 */
import http from '@/api';
import { json2Query } from '@/common/tools';

export default {
  namespaced: true,
  state: {},
  actions: {
    /**
     * 应用列表-获取平台管理应用列表
     */
    getPlatformApps({}, { queryParams }) {
      const url = `${BACKEND_URL}/api/plat_mgt/applications/?${json2Query(queryParams)}`;
      return http.get(url);
    },
    /**
     * 应用列表-获取各租户应用数量信息
     */
    getTenantAppStatistics() {
      const url = `${BACKEND_URL}/api/plat_mgt/applications/tenant_app_statistics/`;
      return http.get(url);
    },
    /**
     * 应用列表-获取应用类型
     */
    getAppTypes() {
      const url = `${BACKEND_URL}/api/plat_mgt/applications/types/`;
      return http.get(url);
    },
    /**
     * 应用详情-获取应用详情数据
     */
    getAppDetails({}, { appCode }) {
      const url = `${BACKEND_URL}/api/plat_mgt/applications/${appCode}/`;
      return http.get(url);
    },
    /**
     * 应用详情-更新应用信息
     */
    updateAppInfo({}, { appCode, data }) {
      const url = `${BACKEND_URL}/api/plat_mgt/applications/${appCode}/`;
      return http.post(url, data);
    },
    /**
     * 应用详情-更新部署集群
     */
    updateDeployCluster({}, { appCode, moduleId, env, data }) {
      const url = `${BACKEND_URL}/api/plat_mgt/applications/${appCode}/modules/${moduleId}/envs/${env}/cluster/`;
      return http.put(url, data);
    },
    /**
     * 特性管理-获取特性列表
     */
    getFeatureList({}, { appCode }) {
      const url = `${BACKEND_URL}/api/plat_mgt/applications/${appCode}/feature_flags/`;
      return http.get(url);
    },
    /**
     * 特性管理-更新应用特性
     */
    updateFeatureFlags({}, { appCode, data }) {
      const url = `${BACKEND_URL}/api/plat_mgt/applications/${appCode}/feature_flags/`;
      return http.put(url, data);
    },
    /**
     * 成员管理-获取成员列表
     */
    getMembers({}, { appCode }) {
      const url = `${BACKEND_URL}/api/plat_mgt/applications/${appCode}/members/`;
      return http.get(url);
    },
    /**
     * 成员管理-添加成员
     */
    addMember({}, { appCode, postParams }) {
      const url = `${BACKEND_URL}/api/plat_mgt/applications/${appCode}/members/`;
      return http.post(url, postParams);
    },
    /**
     * 成员管理-角色更新
     */
    updateRole({}, { appCode, id, params }) {
      const url = `${BACKEND_URL}/api/plat_mgt/applications/${appCode}/members/${id}/`;
      return http.put(url, params);
    },
    /**
     * 成员管理-删除成员
     */
    deleteMember({}, { appCode, id }) {
      const url = `${BACKEND_URL}/api/plat_mgt/applications/${appCode}/members/${id}/`;
      return http.delete(url);
    },
    /**
     * 增强服务-获取服务列表
     */
    getBoundServices({}, { appCode }) {
      const url = `${BACKEND_URL}/api/plat_mgt/applications/${appCode}/services/bound_attachments/`;
      return http.get(url);
    },
    /**
     * 增强服务-分配增强服务实例
     */
    assignEnhancedServiceInstance({}, { appCode, moduleId, env, serviceId }) {
      const url = `${BACKEND_URL}/api/plat_mgt/applications/${appCode}/modules/${moduleId}/envs/${env}/services/${serviceId}/instance/`;
      return http.post(url);
    },
    /**
     * 增强服务-解绑服务实例
     */
    unassignServiceInstance({}, { appCode, moduleId, env, serviceId, instanceId }) {
      const url = `${BACKEND_URL}/api/plat_mgt/applications/${appCode}/modules/${moduleId}/envs/${env}/services/${serviceId}/instance/${instanceId}/`;
      return http.delete(url);
    },
    /**
     * 增强服务-获取增强服务实例凭证
     */
    getCredentials({}, { appCode, moduleId, env, serviceId, instanceId }) {
      const url = `${BACKEND_URL}/api/plat_mgt/applications/${appCode}/modules/${moduleId}/envs/${env}/services/${serviceId}/instance/${instanceId}/credentials/`;
      return http.get(url);
    },
    /**
     * 增强服务-获取未绑定增强服务实例（未回收）
     */
    getUnboundAttachments({}, { appCode }) {
      const url = `${BACKEND_URL}/api/plat_mgt/applications/${appCode}/services/unbound_attachments/`;
      return http.get(url);
    },
    /**
     * 增强服务-回收未绑定的增强服务实例
     */
    recycleServiceInstance({}, { appCode, moduleId, serviceId, instanceId }) {
      const url = `${BACKEND_URL}/api/plat_mgt/applications/${appCode}/modules/${moduleId}/services/${serviceId}/instance/${instanceId}/`;
      return http.delete(url);
    },
    /**
     * 平台管理-操作记录
     */
    getPlatformRecords({}, { queryParams }) {
      const url = `${BACKEND_URL}/api/plat_mgt/audit/platform/?${json2Query(queryParams)}`;
      return http.get(url);
    },
    /**
     * 获取平台管理操作记录详情
     */
    getPlatformRecordDetail({}, { recordId }) {
      const url = `${BACKEND_URL}/api/plat_mgt/audit/platform/${recordId}/`;
      return http.get(url);
    },
    /**
     * 应用-操作记录
     */
    getAppRecords({}, { queryParams }) {
      const url = `${BACKEND_URL}/api/plat_mgt/audit/applications/?${json2Query(queryParams)}`;
      return http.get(url);
    },
    /**
     * 获取应用操作记录详情
     */
    getAppRecordDetail({}, { recordId }) {
      const url = `${BACKEND_URL}/api/plat_mgt/audit/applications/${recordId}/`;
      return http.get(url);
    },
    /**
     * 获取操作记录过滤项
     */
    getFilterOptions() {
      const url = `${BACKEND_URL}/api/plat_mgt/audit/filter_options/`;
      return http.get(url);
    },
    /**
     * 成为插件管理员
     */
    becomePluginAdmin({}, { appCode }) {
      const url = `${BACKEND_URL}/api/plat_mgt/applications/${appCode}/plugin/members/`;
      return http.post(url);
    },
    /**
     * 退出插件管理员
     */
    exitPlugin({}, { appCode }) {
      const url = `${BACKEND_URL}/api/plat_mgt/applications/${appCode}/plugin/members/`;
      return http.delete(url);
    },
  },
};
