/* eslint-disable no-undef */
/* eslint-disable no-unused-vars */
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
    云API相关数据
*/
import http from '@/api';
import { json2Query } from '@/common/tools';
import bartOptions from '@/json/bar_chart_default';
import moment from 'moment';

export default {
  namespaced: true,
  state: {
    pluginFeatureFlags: {},
    chartData: bartOptions,
    // 当前插件的基础信息
    curPluginInfo: {},
    // 当前插件的当前发布版本
    curRelease: {},
    pluginApplyUrl: '',
  },
  getters: {
    chartData: state => state.chartData,
  },
  mutations: {
    /**
     * 设置当前正在查看的发布版本
     * @param {Object} params 请求参数：release
     */
    updateCurRelease(stage, release) {
      stage.curRelease = release;
    },
    updatePluginFeatureFlags(state, data) {
      state.pluginFeatureFlags = data;
    },
    updateChartData(state, data) {
      const chartOptions = JSON.parse(JSON.stringify(bartOptions));
      chartOptions.series = [
        {
          type: 'bar',
          data: data.series,
        },
      ];
      const timestamps = data.timestamps.map((item) => {
        // 时间处理
        item = moment.unix(item).format('YYYY/MM/DD hh:mm:ss');
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
        formatter(params, ticket, callback) {
          return `${params.value}次<br/>${params.name}`;
        },
      };
      state.chartData = chartOptions;
    },
    updatePluginInfo(state, { pluginId, pluginTypeId, data }) {
      state.curPluginInfo = data;
    },
    updatePluginApplyUrl(state, url) {
      state.pluginApplyUrl = url;
    },
  },
  actions: {
    /**
     * --
     * @param {Object} params 请求参数：无
     */
    getPlugins({ commit, state }, { pageParams, statusParams, languageParams, pdIdParams }, config = {}) {
      let url = `${BACKEND_URL}/api/bkplugins/lists/?${json2Query(pageParams)}`;
      if (pdIdParams && pdIdParams.length) {
        url += `&${pdIdParams}`;
      }
      if (statusParams && statusParams.length) {
        url += `&${statusParams}`;
      }
      if (languageParams && languageParams.length) {
        url += `&${languageParams}`;
      }
      return http.get(url, config);
    },
    /**
     * --
     * @param {Object} params 请求参数：appCode
     */
    getVersionsManagerList({ commit, state }, { data, pageParams, statusParams }, config = {}) {
      let url = `${BACKEND_URL}/api/bkplugins/${data.pdId}/plugins/${data.pluginId}/releases/?${json2Query(pageParams)}`;
      if (statusParams && statusParams.length) {
        url += `&${statusParams}`;
      }
      return http.get(url, config);
    },
    /**
     * --
     * @param {Object} params 请求参数：无
     */
    getPluginsTypeList({ commit, state }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/plugin_definitions/schemas/`;
      return http.get(url, config);
    },

    /**
     * --
     * @param {Object} params 请求参数：无
     */
    savePlugins({ commit, state }, data, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${data.pd_id}/plugins/`;
      delete data.pd_id;
      return http.post(url, data, config);
    },

    /**
     * 获取插件详情
     * @param {Object} params 请求参数：pdId, pluginId
     */
    getPluginDetail({ commit, state }, { pdId, pluginId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/`;
      return http.get(url, config);
    },

    /**
     * 获取插件过滤字段
     * @param {Object} params 请求参数：pdId, pluginId, releaseId
     */
    getPluginFilterParams({ commit, state }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/filter_params/`;
      return http.get(url, {}, config);
    },

    /**
     * 获取创建版本发布的表单格式
     * @param {Object} params 请求参数：pdId, pluginId
     */
    getNewVersionFormat({ commit, state }, { pdId, pluginId, type }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/releases/schema/?type=${type}`;
      return http.get(url, config);
    },

    /**
     * 获取版本详情
     * @param {Object} params 请求参数：pdId, pluginId, releaseId
     */
    getReleaseDetail({ commit, state }, { pdId, pluginId, releaseId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/releases/${releaseId}/`;
      return http.get(url, config);
    },

    /**
     * 新建版本
     * @param {Object} params 请求参数：pdId, pluginId
     */
    createVersion({ commit, state }, { pdId, pluginId, data }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/releases/`;
      return http.post(url, data, config);
    },

    /**
     * 获取发布步骤详情
     * @param {Object} params 请求参数：pdId, pluginId, releaseId, stageId
     */
    getPluginReleaseStage({ commit, state }, { pdId, pluginId, releaseId, stageId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/releases/${releaseId}/stages/${stageId}/`;
      return http.get(url, config);
    },

    /**
     * 重新执行发布步骤
     */
    rerunStage({ commit, state }, { pdId, pluginId, releaseId, stageId, data = {} }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/releases/${releaseId}/stages/${stageId}/rerun/`;
      return http.post(url, data, config);
    },

    /**
     * 获取插件信息
     * @param {Object} params 请求参数：pdId, pluginId
     */
    getPluginInfo({ commit, state }, { pluginId, pluginTypeId }) {
      const url = `${BACKEND_URL}/api/bkplugins/${pluginTypeId}/plugins/${pluginId}/`;
      commit('updateAppLoading', true, { root: true });
      return http
        .get(url)
        .then((response) => {
          commit('updatePluginInfo', { pluginId, pluginTypeId, data: response });
          return response;
        })
        .catch((err) => {
          if (err.apply_url_for_dev) {
            commit('updatePluginApplyUrl', err.apply_url_for_dev);
          }
          return err;
        })
        .finally(() => {
          commit('updateAppLoading', false, { root: true });
        });
    },

    /**
     * 上传插件logo
     *
     * @param {Object} params 请求参数：pdId, pluginId
     * @param {Object} config ajax配置
     */
    uploadPluginLogo({ commit, state }, { pdId, pluginId, data }, config) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/logo/`;
      return http.put(url, data, config);
    },

    /**
     * 获取基本信息
     * @param {Object} params 请求参数：pdId, pluginId
     */
    getPluginBaseInfo({ commit, state }, { pdId, pluginId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/`;
      return http.get(url, config);
    },

    /**
     * 获取完善市场信息应用分类信息
     * @param {Object} params 请求参数：pdId, pluginId, releaseId, stageId
     */
    getCategoryList({ commit, state }, { pdId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/plugin_definitions/${pdId}/market_schema/`;
      return http.get(url, config);
    },

    /**
     * 保存基本信息
     * @param {Object} params 请求参数：pdId, pluginId
     */
    updatePluginBaseInfo({ commit, state }, { pdId, pluginId, data }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/`;
      return http.post(url, data, config);
    },

    /**
     * 保存基本信息-更多信息
     * @param {Object} params 请求参数：pdId, pluginId
     */
    updatePluginMoreInfo({ commit, state }, { pdId, pluginId, data }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/extra_fields/`;
      return http.post(url, data, config);
    },

    /**
     * 保存市场信息
     * @param {Object} params 请求参数：pdId, pluginId, releaseId, data
     */
    saveMarketInfo({ commit, state }, { pdId, pluginId, data }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/market/`;
      return http.post(url, data, config);
    },

    /**
     * 获取标准化日志
     * @param {Object} params 请求参数：pdId, pluginId
     */
    getPluginLogList({ commit, state }, { pdId, pluginId, pageParams, data }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/logs/standard_output/?${json2Query(pageParams)}`;
      return http.post(url, data, config);
    },

    /**
     * 获取市场信息
     * @param {Object} params 请求参数：pdId, pluginId, releaseId, data
     */
    getMarketInfo({ commit, state }, { pdId, pluginId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/market/`;
      return http.get(url, config);
    },

    /**
     * 下一步
     * @param {Object} params 请求参数：pdId, pluginId, releaseId
     */
    nextStage({ commit, state }, { pdId, pluginId, releaseId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/releases/${releaseId}/next/`;
      return http.post(url, {}, config);
    },

    /**
     * 终止发布
     * @param {Object} params 请求参数：pdId, pluginId, releaseId
     */
    cancelRelease({ commit, state }, { pdId, pluginId, releaseId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/releases/${releaseId}/cancel/`;
      return http.post(url, {}, config);
    },

    /**
     * 重新发布
     * @param {Object} params 请求参数：pdId, pluginId, releaseId
     */
    republishRelease({ commit, state }, { pdId, pluginId, releaseId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/releases/${releaseId}/reset/`;
      return http.post(url, {}, config);
    },

    /**
     * 部署上一步
     * @param {Object} params 请求参数：pdId, pluginId, releaseId
     */
    backRelease({ commit, state }, { pdId, pluginId, releaseId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/releases/${releaseId}/back/`;
      return http.post(url, {}, config);
    },

    /**
     * 获取访问日志数据
     * @param {Object} params 请求参数：pdId, pluginId, releaseId
     */
    getAccessLogList({ commit, state }, { pdId, pluginId, pageParams, data }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/logs/ingress_logs/?${json2Query(pageParams)}`;
      return http.post(url, data, config);
    },

    /**
     * 获取访问日志图表数据
     * @param {Object} params 请求参数：pdId, pluginId
     */
    getLogChartData({ commit, state }, { pdId, pluginId, pageParams, data }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/logs/aggregate_date_histogram/ingress/?${json2Query(pageParams)}`;
      return http.post(url, data, config);
    },

    /**
     * 获取结构化日志字段设置
     * @param {Object} params 请求参数：pdId, pluginId
     */
    getFilterData({ commit, state }, { pdId, pluginId, params, data }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/logs/aggregate_fields_filters/structure/?${json2Query(params)}`;
      return http.post(url, data, config);
    },

    /**
     * 获取结构化图表数据
     * @param {Object} params 请求参数：pdId, pluginId
     */
    getCustomChartData({ commit, state }, { pdId, pluginId, params, data }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/logs/aggregate_date_histogram/structure/?${json2Query(params)}`;
      return http.post(url, data, config);
    },

    /**
     * 获取结构化日志数据
     * @param {Object} params 请求参数：pdId, pluginId
     */
    getCustomLogList({ commit, state }, { pdId, pluginId, params, data }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/logs/structure_logs/?${json2Query(params)}`;
      return http.post(url, data, config);
    },

    getGitCompareUrl({ commit, state }, { pdId, pluginId, fromRevision, toRevision }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/repo/commit-diff-external/${fromRevision}/${toRevision}/`;
      return http.get(url, {}, config);
    },

    /**
     * 删除插件
     */
    deletePlugin({ commit, state }, { pdId, pluginId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/ `;
      return http.delete(url, config);
    },

    /**
     * 获取配置管理表单配置
     * @param {Object} params 请求参数：pdId
     */
    getConfigurationSchema({ commit, state }, { pdId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/plugin_definitions/${pdId}/configuration_schema/`;
      return http.get(url, {}, config);
    },

    /**
     * 获取配置项
     * @param {Object} params 请求参数：pdId, pluginId
     */
    getEnvVarList({ commit, state }, { pdId, pluginId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/configurations/`;
      return http.get(url, {}, config);
    },

    /**
     * 添加/更新配置项
     * @param {Object} params 请求参数：pdId, pluginId
     */
    editEnvVar({ commit, state }, { pdId, pluginId, data }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/configurations/`;
      return http.post(url, data, config);
    },

    /**
     * 删除配置项
     * @param {Object} params 请求参数：pdId, pluginId
     */
    deleteEnvVar({ commit, state }, { pdId, pluginId, configId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/configurations/${configId}/`;
      return http.delete(url, config);
    },

    /**
     * 获取最新动态
     * @param {Object} params 请求参数：pdId, pluginId
     */
    getPluginOperations({ commit, state }, { pdId, pluginId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/operations/`;
      return http.get(url, {}, config);
    },

    /**
     * 下架插件
     * @param {Object} params 请求参数：pdId, pluginId
     */
    offShelfPlugin({ commit, state }, { pdId, pluginId, data }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/archive/`;
      return http.post(url, data, config);
    },

    /**
     * 更新当前插件 logo
     * @param {Object} params 请求参数：pdId, pluginId
     */
    updateCurPluginLogo({ commit, state }, { logo }, config = {}) {
      state.curPluginInfo.logo_url = logo;
    },

    /**
     * 概览图表
     * @param {Object} params 请求参数：pdId, pluginId, params
     */
    getChartData({ commit, state }, { pdId, pluginId, params }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/code_statistics/?${json2Query(params)}`;
      return http.get(url, {}, config);
    },

    /**
     * 插件功能开关
     * @param {Object} params 请求参数：pdId, pluginId, params
     */
    getPluginFeatureFlags({ commit, state }, { pdId, pluginId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/feature_flags/`;
      return http.get(url, {}, config);
    },

    /**
     * 获取插件使用方可选插件
     * @param {Object} params 请求参数：
     */
    getPluginDistributors({ commit, state }, config = {}) {
      const url = `${BACKEND_URL}/api/bk_plugin_distributors/`;
      return http.get(url, {}, config);
    },

    /**
     * 获取插件使用方信息
     * @param {Object} params 请求参数：
     */
    getProfileData({ commit, state }, { pluginId }, config = {}) {
      const url = `${BACKEND_URL}/api/bk_plugins/${pluginId}/profile/`;
      return http.get(url, {}, config);
    },

    /**
     * 插件使用方更新
     */
    updatePluginUser({ commit, state }, { pluginId, data }, config = {}) {
      const url = `${BACKEND_URL}/api/bk_plugins/${pluginId}/distributors/`;
      return http.put(url, data, config);
    },

    /**
     * 获取已授权插件使用方
     * @param {Object} params 请求参数：
     */
    getAuthorizedUse({ commit, state }, { pluginId }, config = {}) {
      const url = `${BACKEND_URL}/api/bk_plugins/${pluginId}/distributors/`;
      return http.get(url, {}, config);
    },

    /**
     * 插件代码仓库概览信息
     * @param {Object} params 请求参数：
     */
    getStoreOverview({ commit, state }, { pdId, pluginId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/overview/`;
      return http.get(url, {}, config);
    },

    /**
     * 获取插件关联的蓝鲸应用信息
     * 目前仅蓝鲸插件类型的插件有关联蓝鲸应用
     * @param {Object} params 请求参数：
     */
    async getPluginAppInfo({ commit, dispatch }, { pdId, pluginId }, config = {}) {
      // plugin 默认为 default
      const moduleId = 'default';
      await dispatch('getAppInfo', { appCode: pluginId, moduleId }, { root: true });
      await dispatch('getAppFeature', { appCode: pluginId }, { root: true });
      commit('updateCurAppByCode', { appCode: pluginId, moduleId }, { root: true });
    },

    /**
     * 插件部署信息
     * @param {Object} params 请求参数：pluginId
     */
    getPluginAccessEntry({ commit, state }, { pluginId }, config) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${pluginId}/modules/default/envs/prod/released_state/`;
      return http.get(url, config);
    },

    /**
     * 上架插件
     */
    publishPlugin({ commit, state }, { pluginId, data }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/bk-udc/plugins/${pluginId}/reactivate/`;
      return http.post(url, data, config);
    },

    /**
     * 获取插件基本信息
     * @param {Object} params appCode
     */
    getPluginBaseInfoData({ commit, state }, { appCode }, config) {
      const url = `${BACKEND_URL}/api/bk_plugins/${appCode}/profile/`;
      return http.get(url, config);
    },

    /**
     * 获取已授权插件
     * @param {Object} params appCode
     */
    getAuthorizedPlugins({ commit, state }, { appCode }, config) {
      const url = `${BACKEND_URL}/api/bk_plugins/${appCode}/distributors/`;
      return http.get(url, config);
    },

    /**
     * 更新插件基本信息
     */
    updatePluginBseInfo({ commit, state }, { appCode, data }, config = {}) {
      const url = `${BACKEND_URL}/api/bk_plugins/${appCode}/profile/`;
      return http.patch(url, data, config);
    },

    /**
     * 更新步骤状态
     * @param {Object} params 请求参数：pdId, pluginId, releaseId, stageId
     */
    updateStepStatus({ commit, state }, { pdId, pluginId, releaseId, stageId, data }, config) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/releases/${releaseId}/stages/${stageId}/status/`;
      return http.post(url, data, config);
    },

    /**
     * 发布者
     * @param {Object} params 请求参数：pdId, pluginId, data
     */
    updatePublisher({ commit, state }, { pdId, pluginId, data }, config) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/publisher/`;
      return http.post(url, data, config);
    },

    /**
     * 获取可见范围数据
     * @param {Object} params 请求参数：pdId, pluginId
     */
    getVisibleRange({}, { pdId, pluginId }, config) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/visible_range/`;
      return http.get(url, {}, config);
    },

    /**
     * 可见范围
     * @param {Object} params 请求参数：pdId, pluginId, data
     */
    updateVisibleRange({}, { pdId, pluginId, data }, config) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/visible_range/`;
      return http.post(url, data, config);
    },
  },
};
