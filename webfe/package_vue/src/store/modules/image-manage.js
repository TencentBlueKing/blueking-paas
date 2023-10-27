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
    镜像管理相关 vuex 模块
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
         * 获取镜像列表
         *
         * @param {Object} params appCode, moduleNamet
         */
    getImageList({ commit, state }, { appCode, moduleName, pageParams }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleName}/build/artifact/image?${json2Query(pageParams)}`;
      return http.get(url, config);
    },
    /**
         * 获取镜像详情
         *
         * @param {Object} params appCode, moduleNamet
         */
    getImageDetail({ commit, state }, { appCode, moduleName, buildId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleName}/build/artifact/image/${buildId}`;
      return http.get(url, config);
    },
    /**
         * 获取构建历史
         *
         * @param {Object} params appCode, moduleNamet
         */
    getBuildhistoryList({ commit, state }, { appCode, moduleName, pageParams }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleName}/build_process?${json2Query(pageParams)}`;
      return http.get(url, config);
    },

    /**
         * 获取构建详情
         *
         * @param {Object} params appCode, moduleNamet
         */
    getBuildDetail({ commit, state }, { appCode, moduleName, id }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleName}/deployments/${id}/result`;
      return http.get(url, config);
    },
  },
};
