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
    创建app
*/
import http from '@/api';

export default {
  namespaced: true,
  state: {
    isAdvancedOptions: false,
  },
  getters: {},
  mutations: {
    updateAdvancedOptions(state, data) {
      state.isAdvancedOptions = data;
    },
  },
  actions: {
    /**
     * 获取增强服务实例
     */
    getServicesByTmpl({}, { language }, config = {}) {
      const url = `${BACKEND_URL}/api/services/init_templates/${language}`;
      return http.get(url, config);
    },

    /**
     * 获取与应用创建有关的可选项
     */
    getOptions({}, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/creation/options/`;
      return http.get(url, config);
    },

    /**
     * 创建外链应用
     */
    createExternalLinkApp({}, { data }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/third-party/`;
      return http.post(url, data, config);
    },

    /**
     * 获取新建代码仓库下拉列表
     * @param {Object} type - 代码仓库类型
     */
    getNewCodeRepositoryOptions({}, { type }) {
      const url = `${BACKEND_URL}/api/sourcectl/${type}/groups/`;
      return http.get(url);
    },
  },
};
