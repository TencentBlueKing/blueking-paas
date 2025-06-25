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
    日志查询相关数据
*/
import http from '@/api';
import bartOptions from '@/json/bar_chart_default';
import moment from 'moment';

// store
const state = {
  chartData: bartOptions,
  filterData: [],
  logList: [],
  accessLogList: [],
  streamLogList: [],
  envList: [],
  processList: [],
  streamList: [],
  fieldList: [],
};

// getters
const getters = {
  chartData: state => state.chartData,
};

// mutations
const mutations = {
  updateChartData(state, data) {
    const chartOptions = JSON.parse(JSON.stringify(bartOptions));
    chartOptions.series = [{
      type: 'bar',
      data: data.series,
    }];
    const timestamps = data.timestamps.map((item) => {
      // 时间处理
      item = moment.unix(item).format('YYYY-MM-DD HH:mm:ss');
      return item.substring(5);
    });
    chartOptions.xAxis.data = timestamps;
    chartOptions.tooltip = {
      trigger: 'item',
      showDelay: 0,
      hideDelay: 50,
      transitionDuration: 0,
      borderRadius: 2,
      borderWidth: 1,
      padding: 5,
      // eslint-disable-next-line no-unused-vars
      formatter(params, ticket, callback) {
        return `${params.value}次<br/>${params.name}`;
      },
    };
    state.chartData = chartOptions;
  },

  clearData(state) {
    state.envList = [];
    state.streamList = [];
    state.processList = [];
  },

  // TODO: 删除 updateFilterData/updateLogList/updateAccessLogList 等函数
  updateFilterData(state, data) {
    const filters = [];
    const fieldList = [];
    data.forEach((item) => {
      const condition = {
        id: item.key,
        name: item.name,
        text: item.chinese_name || item.name,
        list: [],
      };
      item.options.forEach((option) => {
        condition.list.push({
          id: option[0],
          text: option[0],
        });
      });
      if (condition.name === 'environment') {
        state.envList = condition.list;
      } else if (condition.name === 'process_id') {
        state.processList = condition.list;
      } else if (condition.name === 'stream') {
        state.streamList = condition.list;
      } else {
        fieldList.push(condition);
      }
      filters.push(condition);
    });
    state.filterData = filters;
    state.fieldList = fieldList;
  },

  updateLogList(state, data) {
    // eslint-disable-next-line no-prototype-builtins
    if (!data.hasOwnProperty('isToggled')) {
      data.isToggled = false;
    }
    state.logList = data;
  },

  updateAccessLogList(state, data) {
    // eslint-disable-next-line no-prototype-builtins
    if (!data.hasOwnProperty('isToggled')) {
      data.isToggled = false;
    }
    state.accessLogList = data;
  },
};

// actions
function queryStringify(params) {
  const queryParams = [];
  for (const key in params) {
    if (params[key]) {
      queryParams.push(`${key}=${encodeURIComponent(params[key])}`);
    }
  }
  const queryString = queryParams.join('&');
  return queryString;
}
const actions = {
  getChartData({ commit }, { appCode, moduleId, params, filter }) {
    const queryString = queryStringify(params);
    const logTypeChoices = { STRUCTURED: 'structured', STANDARD_OUTPUT: 'stdout', INGRESS: 'ingress' };
    const logType = logTypeChoices[params.log_type];
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/log/${logType}/date_histogram/?${queryString}`;

    return http.post(url, filter).then((res) => {
      commit('updateChartData', res);
      return res;
    });
  },

  getFilterData({}, { appCode, moduleId, params }) {
    const queryString = queryStringify(params);
    const logTypeChoices = { STRUCTURED: 'structured', STANDARD_OUTPUT: 'stdout', INGRESS: 'ingress' };
    const logType = logTypeChoices[params.log_type];
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/log/${logType}/fields_filters/?${queryString}`;
    return http.post(url);
  },

  getLogList({ commit }, { appCode, moduleId, params, page, pageSize, filter }) {
    const queryString = queryStringify(params);
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/log/structured/list/?page=${page}&page_size=${pageSize}&${queryString}`;
    return http.post(url, filter).then((res) => {
      commit('updateLogList', res.logs);
      return res;
    });
  },

  getAccessLogList({ commit }, { appCode, moduleId, params, page, pageSize, filter }) {
    const queryString = queryStringify(params);
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/log/ingress/list/?page=${page}&page_size=${pageSize}&${queryString}`;
    return http.post(url, filter).then((res) => {
      commit('updateAccessLogList', res.logs);
      return res;
    });
  },

  getStreamLogList({}, { appCode, moduleId, params, filter }) {
    const queryString = queryStringify(params);
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/log/stdout/list/?${queryString}`;
    return http.post(url, filter);
  },

  /**
   * 获取清洗规则
   */
  getCleaningRules({}, { appCode, moduleId }) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/log/config/builtin/json/`;
    return http.get(url);
  },

  /**
   * 获取最近一次重启日志
   * @param {Object} params 请求参数：appCode, moduleId, env, instanceName, processType
   */
  getPreviousLogs({}, { appCode, moduleId, env, processType, instanceName }) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/envs/${env}/processes/${processType}/instances/${instanceName}/previous_logs/`;
    return http.get(url);
  },

  /**
   * 下载重启日志
   *  @param {Object} params 请求参数：appCode, moduleId, env, instanceName, processType
   */
  downloadPreviousLogs({}, { appCode, moduleId, env, processType, instanceName }) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/envs/${env}/processes/${processType}/instances/${instanceName}/previous_logs/download/`;
    return http.get(url, { responseType: 'blob' });
  },

  /**
   * 获取实例实时日志、最近一次重启日志
   * @param {Object} params 请求参数：appCode, moduleId, env, instanceName, processType, previous(true=重启日志、false=实时日志)
   */
  getInstanceLog({}, { appCode, moduleId, env, processType, instanceName, previous, lines }) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/envs/${env}/processes/${processType}/instances/${instanceName}/logs/?previous=${previous}&tail_lines=${lines}`;
    return http.get(url);
  },

  /**
   * 下载实例重启日志、最近一次重启日志
   *  @param {Object} params 请求参数：appCode, moduleId, env, instanceName, processType
   */
  downloadInstanceLog({}, { appCode, moduleId, env, processType, instanceName, previous }) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/envs/${env}/processes/${processType}/instances/${instanceName}/logs/download/?previous=${previous}`;
    return http.get(url, { responseType: 'blob' });
  },
};

export default {
  namespaced: true,
  state,
  getters,
  mutations,
  actions,
};
