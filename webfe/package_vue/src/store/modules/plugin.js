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

export default {
  namespaced: true,
  state: {
    pluginData: {},
    stagesData: []
  },
  getters: {},
  mutations: {
    updatePluginData (state, data) {
      state.pluginData = data;
    },
    updateStagesData (state, data) {
      state.stagesData = data;
    }
  },
  actions: {
    /**
         * --
         * @param {Object} params 请求参数：无
         */
    getPlugins ({ commit, state }, { pageParams }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/lists/?${json2Query(pageParams)}`;
      return http.get(url, config);
    },
    /**
         * --
         * @param {Object} params 请求参数：appCode
         */
    getVersionsManagerList ({ commit, state }, { data, pageParams }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${data.pdId}/plugins/${data.pluginId}/releases/?${json2Query(pageParams)}`;
      return http.get(url, config);
    },
    /**
         * --
         * @param {Object} params 请求参数：无
         */
    getPluginsTypeList ({ commit, state }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/plugin_definitions/schemas/`;
      return http.get(url, config);
    },

    /**
         * --
         * @param {Object} params 请求参数：无
         */
    savePlugins ({ commit, state }, data, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${data.pd_id}/plugins/`;
      delete data.pd_id;
      return http.post(url, data, config);
    },

    /**
         * 获取插件详情
         * @param {Object} params 请求参数：pdId, pluginId
         */
    getPluginDetail ({ commit, state }, { pdId, pluginId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/`;
      return http.get(url, config);
    },

    /**
         * 获取插件过滤字段
         * @param {Object} params 请求参数：pdId, pluginId, releaseId
         */
    getPluginFilterParams ({ commit, state }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/filter_params/`;
      return http.get(url, {}, config);
    },

    /**
         * 获取创建版本发布的表单格式
         * @param {Object} params 请求参数：pdId, pluginId
         */
    getNewVersionFormat ({ commit, state }, { pdId, pluginId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/releases/schema/`;
      return http.get(url, config);
    },

    /**
         * 获取版本详情
         * @param {Object} params 请求参数：pdId, pluginId, releaseId
         */
    getVersionDetail ({ commit, state }, { pdId, pluginId, releaseId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/releases/${releaseId}/`;
      return http.get(url, config);
    },

    /**
         * 新建版本
         * @param {Object} params 请求参数：pdId, pluginId
         */
    createVersion ({ commit, state }, { pdId, pluginId, data }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/releases/`;
      return http.post(url, data, config);
    },

    /**
         * 获取部署详情信息
         * @param {Object} params 请求参数：pdId, pluginId, releaseId, stageId
         */
    getPluginRelease ({ commit, state }, { pdId, pluginId, releaseId, stageId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/releases/${releaseId}/stages/${stageId}/`;
      return http.get(url, config);
    },

    /**
         * 重新部署
         */
    pluginDeploy ({ commit, state }, { pdId, pluginId, releaseId, stageId, data }, config = {}) {
      // /api/bkplugins/{pd_id}/plugins/{plugin_id}/releases/{release_id}/stages/{stage_id}/rerun/
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/releases/${releaseId}/stages/${stageId}/rerun/`;
      return http.post(url, data, config);
    },

    /**
         * 获取基本信息
         * @param {Object} params 请求参数：pdId, pluginId
         */
    getPluginBaseInfo ({ commit, state }, { pdId, pluginId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/`;
      return http.get(url, config);
    },

    /**
         * 获取完善市场信息应用分类信息
         * @param {Object} params 请求参数：pdId, pluginId, releaseId, stageId
         */
    getCategoryList ({ commit, state }, { pdId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/plugin_definitions/${pdId}/market_schema/`;
      return http.get(url, config);
    },

    /**
         * 保存基本信息
         * @param {Object} params 请求参数：pdId, pluginId
         */
    updatePluginBaseInfo ({ commit, state }, { pdId, pluginId, data }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/`;
      return http.post(url, data, config);
    },

    /**
         * 保存市场信息
         * @param {Object} params 请求参数：pdId, pluginId, releaseId, data
         */
    saveMarketInfo ({ commit, state }, { pdId, pluginId, data }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/market/`;
      return http.post(url, data, config);
    },

    /**
         * 获取标准化日志
         * @param {Object} params 请求参数：pdId, pluginId
         */
    getPluginLogList ({ commit, state }, { pdId, pluginId, pageParams, data }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/logs/standard_output/?${json2Query(pageParams)}`;
      return http.post(url, data, config);
    },

    /**
         * 获取市场信息
         * @param {Object} params 请求参数：pdId, pluginId, releaseId, data
         */
    getMarketInfo ({ commit, state }, { pdId, pluginId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/market/`;
      return http.get(url, config);
    },

    /**
         * 下一步
         * @param {Object} params 请求参数：pdId, pluginId, releaseId
         */
    nextRelease ({ commit, state }, { pdId, pluginId, releaseId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/releases/${releaseId}/next/`;
      return http.post(url, {}, config);
    },

    /**
         * 终止发布
         * @param {Object} params 请求参数：pdId, pluginId, releaseId
         */
    cancelRelease ({ commit, state }, { pdId, pluginId, releaseId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/releases/${releaseId}/cancel/`;
      return http.post(url, {}, config);
    },

    /**
         * 获取访问日志数据
         * @param {Object} params 请求参数：pdId, pluginId, releaseId
         */
    getAccessLogList ({ commit, state }, { pdId, pluginId, pageParams, data }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/logs/ingress_logs/?${json2Query(pageParams)}`;
      return http.post(url, data, config);
    },

    getGitCompareUrl ({ commit, state }, { pdId, pluginId, fromRevision, toRevision }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/repo/commit-diff-external/${fromRevision}/${toRevision}/`;
      return http.get(url, {}, config);
    },

    /**
         * 删除插件
         */
    deletePlugin ({ commit, state }, { pdId, pluginId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkplugins/${pdId}/plugins/${pluginId}/ `;
      return http.delete(url, config);
    }
  }
};
