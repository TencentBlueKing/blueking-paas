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
     * 查询日志采集规则列表
     */
    getLogCollectionRuleList({}, { appCode, moduleId }) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/log/custom-collector/`;
      return http.get(url);
    },

    /**
     * 获取采集规则
     */
    getCollectionRules({}, { appCode, moduleId }) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/log/custom-collector-metadata/`;
      return http.get(url);
    },

    /**
     * 新建、编辑采集规则
     */
    editorCollectionRule({}, { appCode, moduleId, data }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/log/custom-collector/`;
      return http.post(url, data, config);
    },

    /**
     * 删除采集规则
     */
    deleteCollectionRule({}, { appCode, moduleId, name }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/log/custom-collector/${name}/`;
      return http.delete(url, {}, config);
    },
  },
};
