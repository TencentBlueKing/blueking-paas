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
    这里管理开发者中心 header 中的搜索功能的状态
    一般用于控制侧边栏的展示
*/
import Vue from 'vue';
import http from '@/api';
import { json2Query } from '@/common/tools';

// actions
const actions = {
  async fetchSearchApp(_, { filterKey, params }) {
    return Vue.http.get(`${BACKEND_URL}/api/bkapps/applications/lists/search?is_active=true&keyword=${filterKey}`, {
      params,
    }).then(res => res.results.map(data => ({
      code: data.application.code,
      name: data.application.name,
      marked: data.marked,
      moduleId: data.default_module_name,
    })), (err) => {
      console.error('fetchSearchApp Error', err);
      return [];
    });
  },
  async fetchSearchDoc(_, filterKey) {
    return Vue.http.get(`${BACKEND_URL}/api/document/search/?format=json&keyword=${filterKey}`).then(res => res, (err) => {
      console.error('fetchSearchDoc Error', err);
      return [];
    });
  },

  /**
     * 获取搜索的应用
     */
  getSearchApp({}, params, config = {}) {
    const url = `${BACKEND_URL}/api/search/applications/?${json2Query(params)}`;
    return http.get(url, config);
  },

  /**
     * 获取搜索的资料文档条目
     */
  getSearchDocs({}, params, config = {}) {
    const url = `${BACKEND_URL}/api/search/bk_docs/?${json2Query(params)}`;
    return http.get(url, config);
  },

  /**
     * 获取搜索的iwiki
     */
  getSearchIwiki({}, params, config = {}) {
    const url = `${BACKEND_URL}/api/search/iwiki/?${json2Query(params)}`;
    return http.get(url, config);
  },
};

export default {
  namespaced: true,
  actions,
};
