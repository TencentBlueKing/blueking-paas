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
    数据统计相关 vuex 模块
*/
import http from '@/api';

import { json2Query } from '@/common/tools';

export default {
  namespaced: true,
  state: {},
  getters: {},
  mutations: {},
  actions: {
    // 查询用户上报的站点配置
    getAnalysisConfig ({ commit, state }, { appCode, siteName, moduleId, env, backendType, engineEnabled }, config = {}) {
      let url = '';
      if (engineEnabled) {
        url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/envs/${env}/analysis/m/${backendType}/config`;
      } else {
        url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/analysis/site/${siteName}/config`;
      }
      return http.get(url, config);
    },

    // 查询当前日志统计功能状态
    getAnalysisStatus ({ commit, state }, { appCode, moduleId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/analysis/ingress/tracking_status/`;
      return http.get(url, config);
    },

    // 用户上报的访问量
    getPvUv ({ commit, state }, { appCode, siteName, params, moduleId, env, backendType, engineEnabled }, config = {}) {
      let url = '';
      if (engineEnabled) {
        url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/envs/${env}/analysis/m/${backendType}/metrics/total?${json2Query(params)}`;
      } else {
        url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/analysis/site/${siteName}/metrics/total?${json2Query(params)}`;
      }
      return http.get(url, config);
    },

    // 访问量曲线数据
    getChartData ({ commit, state }, { appCode, siteName, params, moduleId, env, backendType, engineEnabled }, config = {}) {
      let url = '';
      if (engineEnabled) {
        url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/envs/${env}/analysis/m/${backendType}/metrics/aggregate_by_interval?${json2Query(params)}`;
      } else {
        url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/analysis/site/${siteName}/metrics/aggregate_by_interval?${json2Query(params)}`;
      }
      return http.get(url, config);
    },

    // 以PATH分组的访问量
    getDataByDimension ({ commit, state }, { appCode, siteName, dimension, params, moduleId, env, backendType, engineEnabled }, config = {}) {
      let url = '';
      if (engineEnabled) {
        url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/envs/${env}/analysis/m/${backendType}/metrics/dimension/${dimension}?${json2Query(params)}`;
      } else {
        url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/analysis/site/${siteName}/metrics/dimension/${dimension}?${json2Query(params)}`;
      }
      return http.get(url, config);
    },

    // 手动修改基于日志统计功能状态
    enableLog ({ commit, state }, { appCode, moduleId, params }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/analysis/ingress/tracking_status/?${json2Query(params)}`;
      return http.post(url, params, config);
    },

    // 自定义事件访问量曲线数据
    getEventChartData ({ commit, state }, { appCode, siteName, params, moduleId, env, engineEnabled }, config = {}) {
      let url = '';
      if (engineEnabled) {
        url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/envs/${env}/analysis/event/metrics/aggregate_by_interval?${json2Query(params)}`;
      } else {
        url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/analysis/site/${siteName}/event/metrics/aggregate_by_interval?${json2Query(params)}`;
      }
      return http.get(url, config);
    },

    getEventDetail ({ commit, state }, { appCode, siteName, params, moduleId, dimension, env, category, engineEnabled }, config = {}) {
      let url = '';
      if (engineEnabled) {
        url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/envs/${env}/analysis/event/metrics/c/${category}/d/${dimension}/detail?${json2Query(params)}`;
      } else {
        url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/analysis/site/${siteName}/event/metrics/c/${category}/d/${dimension}/detail?${json2Query(params)}`;
      }
      return http.get(url, config);
    },

    getEventOverview ({ commit, state }, { appCode, siteName, params, moduleId, env, engineEnabled }, config = {}) {
      let url = '';
      if (engineEnabled) {
        url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/envs/${env}/analysis/event/metrics/overview?${json2Query(params)}`;
      } else {
        url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/analysis/site/${siteName}/event/metrics/overview?${json2Query(params)}`;
      }
      return http.get(url, config);
    },

    getEventAnalysisConfig ({ commit, state }, { appCode, siteName, moduleId, env, engineEnabled }, config = {}) {
      let url = '';
      if (engineEnabled) {
        url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/envs/${env}/analysis/event/config`;
      } else {
        url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/analysis/site/${siteName}/event/config`;
      }
      return http.get(url, config);
    },

    getEventEvUv ({ commit, state }, { appCode, siteName, moduleId, env, engineEnabled, params }, config = {}) {
      let url = '';
      if (engineEnabled) {
        url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/envs/${env}/analysis/event/metrics/total?${json2Query(params)}`;
      } else {
        url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/analysis/site/${siteName}/event/metrics/total?${json2Query(params)}`;
      }
      return http.get(url, config);
    }
  }
};
