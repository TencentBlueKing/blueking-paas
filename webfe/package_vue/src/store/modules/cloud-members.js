/*
* Tencent is pleased to support the open source community by making
* 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
* Copyright (C) 2017-2022THL A29 Limited, a Tencent company.  All rights reserved.
* Licensed under the MIT License (the "License").
* You may not use this file except in compliance with the License.
* You may obtain a copy of the License at http://opensource.org/licenses/MIT
* Unless required by applicable law or agreed to in writing,
* software distributed under the License is distributed on
* an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
* either express or implied. See the License for the
* specific language governing permissions and limitations under the License.
*
* We undertake not to change the open source license (MIT license) applicable
*
* to the current version of the project delivered to anyone in the future.
*/

/*
    成员管理
*/
import http from '@/api';

export default {
  namespaced: true,
  state: {},
  getters: {},
  mutations: {},
  actions: {
    /**
         * 获取成员列表
         */
    getMemberList ({ commit, state }, { pdId, pluginId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/members/`;
      return http.get(url, config);
    },

    /**
         * 新增成员
         */
    addMember ({ commit, state }, { pdId, pluginId, postParams }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/members/`;
      return http.post(url, postParams, config);
    },

    /**
         * 退出应用
         */
    quitApplication ({ commit, state }, { pdId, pluginId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/members/leave/`;
      return http.post(url, {}, config);
    },

    /**
         * 删除成员
         */
    deleteRole ({ commit, state }, { pdId, pluginId, username }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/members/${username}/`;
      return http.delete(url, config);
    }
  }
};
