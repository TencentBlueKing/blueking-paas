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
    应用迁移
*/
import http from '@/api';

export default {
  namespaced: true,
  state: {},
  getters: {},
  mutations: {},
  actions: {
    /**
     * 查询迁移状态
     */
    queryMigrationStatus({}, { id }, config = {}) {
      const url = `${BACKEND_URL}/api/mgrlegacy/cloud-native/migration_processes/${id}/`;
      return http.get(url, config);
    },

    /**
     * 查询迁移状态
     */
    getMigrationProcessesLatest({}, { appCode }, config = {}) {
      const url = `${BACKEND_URL}/api/mgrlegacy/cloud-native/applications/${appCode}/migration_processes/latest/`;
      return http.get(url, config);
    },

    /**
     * 迁移前的 check_list 信息接口
     */
    getChecklistInfo({}, { appCode }, config = {}) {
      const url = `${BACKEND_URL}/api/mgrlegacy/applications/${appCode}/checklist_info/`;
      return http.get(url, config);
    },

    /**
     * 触发迁移接口
     */
    triggerMigration({}, { appCode }, config = {}) {
      const url = `${BACKEND_URL}/api/mgrlegacy/cloud-native/applications/${appCode}/migrate/`;
      return http.post(url, {}, config);
    },

    /**
     * 确定迁移接口
     */
    migrationProcessesConfirm({}, { id }, config = {}) {
      const url = `${BACKEND_URL}/api/mgrlegacy/cloud-native/migration_processes/${id}/confirm/`;
      return http.put(url, {}, config);
    },

    /**
     * 获取进程列表
     */
    getProcessesList({}, { appCode, moduleId, env }, config = {}) {
      const url = `${BACKEND_URL}/api/mgrlegacy/applications/${appCode}/modules/${moduleId}/envs/${env}/processes/`;
      return http.get(url, {}, config);
    },

    /**
     * 启停进程（包括扩缩容）
     */
    updateProcess({}, { appCode, moduleId, env, data }, config = {}) {
      const url = `${BACKEND_URL}/api/mgrlegacy/applications/${appCode}/modules/${moduleId}/envs/${env}/processes/`;
      return http.put(url, data, config);
    },

    /**
     * 应用回退
     */
    rollback({}, { appCode }, config = {}) {
      const url = `${BACKEND_URL}/api/mgrlegacy/cloud-native/applications/${appCode}/rollback/`;
      return http.post(url, {}, config);
    },
  },
};
