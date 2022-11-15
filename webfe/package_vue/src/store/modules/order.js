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
    单据相关 vuex 模块
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
         * 获取单据列表
         *
         * @param {Object} params 请求参数：filter_type, appCode, order_by, limit, offset
         */
    getOrderList ({ commit, state }, { filterType, appCode, order_by, limit, offset }, config = {}) {
      const params = {
        order_by,
        limit,
        offset
      };
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/access_control/apply_record/filter_type/${filterType}/?${json2Query(params)}`;
      return http.get(url, config);
    },

    /**
         * 单据操作(通过/驳回)
         *
         * @param {Object} params 请求参数：appCode, type, record_ids, remark
         */
    operateOrder ({ commit, state }, { appCode, type, record_ids, remark }, config = {}) {
      const params = {
        record_ids,
        remark
      };
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/access_control/apply_record/approval_type/${type}/`;
      return http.post(url, params, config);
    }
  }
};
