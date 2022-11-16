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
    用户限制相关 vuex 模块
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
         * 获取用户限制列表
         *
         * @param {Object} params search_term, appCode, order_by, limit, offset
         */
    getUserPermissionList ({ commit, state }, { appCode, order_by, limit, offset, search_term }, config = {}) {
      const params = {
        order_by,
        limit,
        offset,
        search_term
      };
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/access_control/restriction_type/user/strategy/?${json2Query(params)}`;
      return http.get(url, config);
    },

    /**
         * 删除名单
         *
         * @param {Object} params appCode, ids
         */
    deleteUserPermission ({ commit, state }, { appCode, ids }, config = {}) {
      const params = ids.map(item => {
        return `id=${item}`;
      }).join('&');
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/access_control/restriction_type/user/strategy/?${params}`;
      return http.delete(url, {}, config);
    },

    /**
         * 新增用户
         *
         * @param {Object} params 请求参数：appCode, params
         */
    addUser ({ commit, state }, { appCode, params }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/access_control/restriction_type/user/strategy/`;
      return http.post(url, params, config);
    },

    /**
         * 检测用户权限
         *
         * @param {Object} params 请求参数：appCode, params
         */
    checkUserPermissin ({ commit, state }, { appCode }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/access_control/restriction_type/user/switch/`;
      return http.get(url, config);
    },

    /**
         * 设置用户权限
         *
         * @param {Object} params 请求参数：appCode, is_enabled
         */
    setUserPermissin ({ commit, state }, { appCode, is_enabled }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/access_control/restriction_type/user/switch/`;
      return http.post(url, { is_enabled: is_enabled }, config);
    },
    /**
         * 用户权限有效时间续期
         *
         * @param {Object} Obj { appCode, id, params }
         */
    userPermissinRenewal ({ commit, state }, { appCode, id, params }, config = {}) {
      const obj = { ...params };
      if (obj.expires_at === null) {
        delete obj.expires;
      } else {
        delete obj.expires_at;
      }
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/access_control/restriction_type/user/strategy/${id}`;
      return http.patch(url, obj, config);
    },

    /**
         * 获取豁免策略列表
         *
         * @param {Object} params search_term, appCode, order_by, limit, offset
         */
    getExemptList ({ commit, state }, { appCode, order_by, limit, offset, search_term, restriction_type }, config = {}) {
      const params = {
        order_by,
        limit,
        offset,
        search_term,
        restriction_type
      };
      const restrictionType = params.restriction_type;
      delete params.restriction_type;
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/access_exempt/restriction_type/${restrictionType}/strategy/?${json2Query(params)}`;
      return http.get(url, config);
    },

    /**
         * 创建豁免策略
         *
         * @param {Object} params
         */
    createExempt ({ commit, state }, params, config = {}) {
      const { appCode, data } = params;
      const restrictionType = params.restriction_type;
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/access_exempt/restriction_type/${restrictionType}/strategy/`;
      return http.post(url, data, config);
    },

    /**
         * 更新豁免策略
         *
         * @param {Object} params
         */
    updateExempt ({ commit, state }, params, config = {}) {
      const { appCode, data } = params;
      const restrictionType = params.restriction_type;
      const strategyId = params.strategy_id;
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/access_exempt/restriction_type/${restrictionType}/strategy/${strategyId}/`;
      return http.patch(url, data, config);
    },

    /**
         * 删除豁免策略
         *
         * @param {Object} params
         */
    deleteExempt ({ commit, state }, params, config = {}) {
      const appCode = params.appCode;
      const restrictionType = params.restriction_type;
      const strategyId = params.strategy_id;
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/access_exempt/restriction_type/${restrictionType}/strategy/${strategyId}/`;
      return http.delete(url, {}, config);
    },

    /**
         * 批量删除豁免策略
         *
         * @param {Object} params
         */
    batchDeleteExempt ({ commit, state }, params, config = {}) {
      const { appCode, id } = params;
      const restrictionType = params.restriction_type;
      const requestParams = {
        id
      };
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/access_exempt/restriction_type/${restrictionType}/strategy/?${json2Query(requestParams)}`;
      return http.delete(url, {}, config);
    }
  }
};
