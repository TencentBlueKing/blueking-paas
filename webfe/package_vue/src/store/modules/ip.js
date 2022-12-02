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
    ip相关 vuex 模块
*/
import http from '@/api';

import { json2Query } from '@/common/tools';

export default {
  namespaced: true,
  state: {},
  getters: {},
  mutations: {},
  actions: {
    /**
         * 获取ip列表
         *
         * @param {Object} params search_term, appCode, order_by, limit, offset
         */
    getIpList ({ commit, state }, { appCode, order_by, limit, offset, search_term }, config = {}) {
      const params = {
        order_by,
        limit,
        offset,
        search_term
      };
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/access_control/restriction_type/ip/strategy/?${json2Query(params)}`;
      return http.get(url, config);
    },

    /**
         * 删除ip
         *
         * @param {Object} params appCode, ids
         */
    deleteIp ({ commit, state }, { appCode, ids }, config = {}) {
      const params = ids.map(item => {
        return `id=${item}`;
      }).join('&');
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/access_control/restriction_type/ip/strategy/?${params}`;
      return http.delete(url, {}, config);
    },

    /**
         * 新增ip
         *
         * @param {Object} params 请求参数：appCode, params
         */
    addIp ({ commit, state }, { appCode, params }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/access_control/restriction_type/ip/strategy/`;
      return http.post(url, params, config);
    },

    /**
         * 检测ip权限
         *
         * @param {Object} params 请求参数：appCode, params
         */
    checkIpPermissin ({ commit, state }, { appCode }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/access_control/restriction_type/ip/switch/`;
      return http.get(url, config);
    },

    /**
         * 设置ip权限
         *
         * @param {Object} params 请求参数：appCode, is_enabled
         */
    setIpPermissin ({ commit, state }, { appCode, is_enabled }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/access_control/restriction_type/ip/switch/`;
      return http.post(url, { is_enabled: is_enabled }, config);
    },

    /**
         * ip权限有效时间续期
         *
         * @param {Object} Obj { appCode, id, params }
         */
    ipPermissinRenewal ({ commit, state }, { appCode, id, params }, config = {}) {
      const obj = { ...params };
      if (obj.expires_at === null) {
        delete obj.expires;
      } else {
        delete obj.expires_at;
      }
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/access_control/restriction_type/ip/strategy/${id}`;
      return http.patch(url, obj, config);
    }
  }
};
