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
    监控告警
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
     * 获取告警记录列表
     * @param {Object} params 请求参数
     */
    getAlarmList({}, params, config = {}) {
      const requestParams = JSON.parse(JSON.stringify(params));
      delete requestParams.code;
      if (requestParams.search === '') {
        delete requestParams.search;
      }
      if (requestParams.module === '') {
        delete requestParams.module;
      } else {
        requestParams.module = [requestParams.module];
      }
      if (requestParams.env === '') {
        delete requestParams.env;
      } else {
        requestParams.env = [requestParams.env];
      }
      if (requestParams.uuid === '') {
        delete requestParams.uuid;
      }
      if (requestParams.genre === '') {
        delete requestParams.genre;
      } else {
        requestParams.genre = [requestParams.genre];
      }
      if (!requestParams.is_active) {
        delete requestParams.is_active;
      }
      const url = `${BACKEND_URL}/api/monitor/applications/${params.code}/record/query/`;
      return http.post(url, requestParams, config);
    },

    /**
     * 获取告警类型
     * @param {Object} params 请求参数
     */
    getAlarmType({}, params, config = {}) {
      const requestParams = JSON.parse(JSON.stringify(params));
      delete requestParams.appCode;
      const url = `${BACKEND_URL}/api/monitor/applications/${params.appCode}/genre/?${json2Query(requestParams)}`;
      return http.get(url, config);
    },

    /**
     * 获取告警记录详情
     * @param {Object} params 请求参数: appCode, record
     */
    getAlarmDetail({}, { appCode, record }, config = {}) {
      const url = `${BACKEND_URL}/api/monitor/applications/${appCode}/record/${record}/`;
      return http.get(url, config);
    },

    /**
     * 获取个人应用告警
     * @param {Object} params 请求参数
     */
    getPersonalMonitor({}, params, config = {}) {
      const url = `${BACKEND_URL}/api/monitor/record/applications/summary/?${json2Query(params)}`;
      return http.get(url, config);
    },

    /**
     * 获取告警记录列表
     * @param {Object} params 请求参数
     */
    getPersonalAlarmList({}, params, config = {}) {
      const requestParams = JSON.parse(JSON.stringify(params));
      delete requestParams.code;
      const url = `${BACKEND_URL}/api/monitor/applications/${params.code}/record/query/`;
      return http.post(url, requestParams.search, config);
    },

    /**
     * 获取告警记录指标趋势
     * @param {Object} params 请求参数
     */
    getAlarmMetrics({}, params, config = {}) {
      const requestParams = JSON.parse(JSON.stringify(params));
      delete requestParams.code;
      delete requestParams.record;
      const url = `${BACKEND_URL}/api/monitor/applications/${params.code}/record_metrics/${params.record}/?${json2Query(requestParams)}`;
      return http.get(url, config);
    },

    /**
     * 获取蓝鲸监控数据
     * @param {Object} params 请求参数
     */
    getBkAlarmList({}, { appCode, data }, config = {}) {
      const url = `${BACKEND_URL}/api/monitor/applications/${appCode}/alerts/`;
      return http.post(url, data, config);
    },

    /*
     * 获取告警策略
     * @param {Object} appCode 请求参数
     */
    getAlarmStrategies({}, { appCode }, config = {}) {
      // `${BACKEND_URL}/api/monitor/applications/{bk_app.code}/alarm_strategies/?${json2Query(params)}`
      const url = `${BACKEND_URL}/api/monitor/applications/${appCode}/alarm_strategies/`;
      return http.post(url, config);
    },

    /**
     * 查询用户各应用告警数量
     * @param {Object} data 请求参数
     */
    queryAllAppAlerts({}, { data }, config = {}) {
      const url = `${BACKEND_URL}/api/monitor/user/alerts/`;
      return http.post(url, data, config);
    },
  },
};
