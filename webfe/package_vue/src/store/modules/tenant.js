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
* 多租户
*/
import http from '@/api';

export default {
  namespaced: true,
  state: {
    availableClusters: {},
    curTenantData: {},
    clustersStatus: {},
  },
  mutations: {
    updateAvailableClusters(state, data) {
      state.availableClusters = data;
    },
    updateTenantData(state, data) {
      state.curTenantData = data;
    },
    updateClustersStatus(state, { clusterName, status }) {
      state.clustersStatus = {
        ...state.clustersStatus,
        [clusterName]: status,
      };
    },
  },
  actions: {
    /**
     * 获取租户下的人员信息
     */
    searchTenantUsers({}, { keyword, tenantId }) {
      const config = {
        headers: {
          'X-Bk-Tenant-Id': tenantId,
        }
      };
      const apiUrl = window.BK_API_URL_TMPL?.replace('{api_name}', 'bk-user-web/prod');
      const url = `${apiUrl}/api/v3/open-web/tenant/users/-/search/?keyword=${keyword}`;
      return http.get(url, {}, config);
    },
    /**
     * 获取所有租户
     */
    getTenants({}) {
      const url = `${BACKEND_URL}/api/tenants/`;
      return http.get(url);
    },
    /**
     * 获取分配条件类型
     */
    getClusterAllocationPolicyConditionTypes({}) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/cluster_allocation_policy_condition_types/`;
      return http.get(url);
    },
    /**
     * 获取全量集群策略
     */
    getClusterAllocationPolicies({}) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/cluster_allocation_policies/`;
      return http.get(url);
    },
    /**
     * 删除分配策略
     */
    delClusterAllocationPolicies({}, { id }) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/cluster_allocation_policies/${id}/`;
      return http.delete(url);
    },
    /**
     * 获取当前租户可用的集群
     */
    getAvailableClusters({}, { id }) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/tenants/${id}/available_clusters/`;
      return http.get(url);
    },
    /**
     * 新建集群分配策略
     */
    createClusterAllocationPolicies({}, { data }) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/cluster_allocation_policies/`;
      return http.post(url, data);
    },
    /**
     * 更新集群策略
     */
    updateClusterAllocationPolicies({}, { id, data }) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/cluster_allocation_policies/${id}/`;
      return http.put(url, data);
    },
    /**
     * 获取集群列表
     */
    getClusterList({}) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/clusters/`;
      return http.get(url);
    },
    /**
     * 获取集群使用情况
     */
    getClusterAllocationState({}, { clusterName }) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/clusters/${clusterName}/allocation_state/`;
      return http.get(url);
    },
    /**
     * 获取集群状态
     */
    getClustersStatus({}, { clusterName }) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/clusters/${clusterName}/status/`;
      return http.get(url);
    },
    /**
     * 同步节点
     */
    syncNodes({}, { clusterName }) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/clusters/${clusterName}/operations/sync_nodes/`;
      return http.post(url);
    },
    /**
     * 删除集群
     */
    deleteCluster({}, { clusterName }) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/clusters/${clusterName}/`;
      return http.delete(url);
    },
    /**
     * 获取集群详情
     */
    getClusterDetails({}, { clusterName }) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/clusters/${clusterName}/`;
      return http.get(url);
    },
    /**
     * 获取集群组件列表
     */
    getClusterComponents({}, { clusterName }) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/clusters/${clusterName}/components/`;
      return http.get(url);
    },
    /**
     * 获取集群组件详情
     */
     getComponentDetail({}, { clusterName, componentName }) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/clusters/${clusterName}/components/${componentName}/`;
      return http.get(url);
    },
    /**
     * 获取 BCS API 访问地址模板
     */
    getClusterServerUrlTmpl({}) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/bcs/cluster_server_url_tmpl/`;
      return http.get(url);
    },
    /**
     * 获取BCS项目数据
     */
    getBcsProjects({}) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/bcs/projects/`;
      return http.get(url);
    },
    /**
     * 获取BCS集群数据
     */
    getBcsClusters({}, { projectId }) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/bcs/projects/${projectId}/clusters/`;
      return http.get(url);
    },
    /**
     * 新建集群
     */
    createCluster({}, { data }) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/clusters/`;
      return http.post(url, data);
    },
    /**
     * 更新集群
     */
    updateCluster({}, { clusterName, data }) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/clusters/${clusterName}/`;
      return http.put(url, data);
    },
    /**
     * 更新或安装集群组件
     */
    updateComponent({}, { clusterName, componentName, data }) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/clusters/${clusterName}/components/${componentName}/`;
      return http.post(url, data);
    },
    /**
     * 对比待更新组件版本
     */
    getDiffVersion({}, { clusterName, componentName }) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/clusters/${clusterName}/components/${componentName}/operations/diff_version/`;
      return http.get(url);
    },
    /**
     * 获取集群特性可启用项
     */
    getClusterFeatureFlags({}) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/cluster_feature_flags/`;
      return http.get(url);
    },
    /**
     * 获取服务方案
     */
    getPlans({}) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/plans/`;
      return http.get(url);
    },
    /**
     * 获取所属服务
     */
    getPlatformServices({}) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/services/`;
      return http.get(url);
    },
    /**
     * 获取服务分类
     */
    getServicesCategory({}) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/service_category/`;
      return http.get(url);
    },
    /**
     * 获取供应商
     */
    getServicesProviderChoices({}) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/service_provider_choices/`;
      return http.get(url);
    },
    /**
     * 新建服务
     */
    addPlatformService({}, { data }) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/services/`;
      return http.post(url, data);
    },
    /**
     * 编辑服务
     */
    updatePlatformService({}, { serviceId, data }) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/services/${serviceId}/`;
      return http.put(url, data);
    },
    /**
     * 删除本地服务
     */
    deletePlatformService({}, { serviceId }) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/services/${serviceId}/`;
      return http.delete(url);
    },
    /**
     * 添加方案
     */
    addPlan({}, { serviceId, tenantId, data }) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/services/${serviceId}/tenants/${tenantId}/plans/`;
      return http.post(url, data);
    },
    /**
     * 修改方案
     */
    modifyPlan({}, { serviceId, tenantId, planId, data }) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/services/${serviceId}/tenants/${tenantId}/plans/${planId}/`;
      return http.put(url, data);
    },
    /**
     * 删除方案
     */
    deletePlan({}, { serviceId, tenantId, planId }) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/services/${serviceId}/tenants/${tenantId}/plans/${planId}/`;
      return http.delete(url);
    },
     /**
     * 获取租户下的服务-方案
     */
    getServicePlansUnderTenant({}, { tenantId, serviceId }) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/services/${serviceId}/tenants/${tenantId}/plans/`;
      return http.get(url);
    },
    /**
     * 获取方案下的资源池
     */
    getPreCreatedInstances({}, { serviceId, tenantId, planId }) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/services/${serviceId}/tenants/${tenantId}/plans/${planId}/ `;
      return http.get(url);
    },
    /**
     * 添加资源池
     */
    addResourcePool({}, { planId, data }) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/plans/${planId}/pre_created_instances/`;
      return http.post(url, data);
    },
    /**
     * 修改资源池
     */
    updateResourcePool({}, { planId, id, data }) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/plans/${planId}/pre_created_instances/${id}/`;
      return http.put(url, data);
    },
    /**
     * 删除资源池
     */
    deleteResourcePool({}, { planId, id }) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/plans/${planId}/pre_created_instances/${id}/`;
      return http.delete(url);
    },
    /**
     * 获取服务配置方案
     */
    getBindingPolicies({}, { serviceId }) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/services/${serviceId}/binding_policies/`;
      return http.get(url);
    },
    /**
     * 新建配置方案
     */
    addBindingPolicies({}, { serviceId, data }) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/services/${serviceId}/binding_policies/`;
      return http.post(url, data);
    },
    /**
     * 更新配置方案
     */
    updateBindingPolicies({}, { serviceId, data }) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/services/${serviceId}/binding_policies/`;
      return http.put(url, data);
    },
    /**
     * 删除配置方案
     */
    deleteBindingPolicies({}, { tenantId, serviceId }) {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/services/${serviceId}/binding_policies?tenant_id=${tenantId}`;
      return http.delete(url);
    },
    /**
     * 获取概览增强服务列表
     */
    getOverviewServices() {
      const url = `${BACKEND_URL}/api/plat_mgt/infras/services/`;
      return http.get(url);
    },
    /**
     * 获取概览各个租户的配置状态（行数据）
     */
    getTenantConfigStatuses() {
      const url = `${BACKEND_URL}/api/plat_mgt/overview/tenant_config_statuses/`;
      return http.get(url);
    },
  },
};
