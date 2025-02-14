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
    curTenantData: {}
  },
  mutations: {
    updateAvailableClusters(state, data) {
      state.availableClusters = data;
    },
    updateTenantData(state, data) {
      state.curTenantData = data;
    },
  },
  actions: {
    /**
     * 获取所有租户
     */
    getTenants({}) {
      const url = `${BACKEND_URL}/api/tenants/`;
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
  },
};
