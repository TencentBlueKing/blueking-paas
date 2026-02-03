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
    云API相关数据
*/
import http from '@/api';

import { json2Query } from '@/common/tools';

export default {
  namespaced: true,
  state: {
    cloudAppData: {},
    isPageEdit: false,
    processPageEdit: false,
    hookPageEdit: false,
    isModuleInfoEdit: false,
  },
  getters: {},
  mutations: {
    updateCloudAppData(state, data) {
      if (data?.spec?.build) {
        // eslint-disable-next-line no-param-reassign
        data.spec.build.image = data.spec.build.image || null;
        // eslint-disable-next-line no-param-reassign
        data.spec.build.imageCredentialsName = data.spec.build.imageCredentialsName || null;
      }
      state.cloudAppData = data;
    },
    updatePageEdit(state, data) {
      state.isPageEdit = data;
    },
    updateProcessPageEdit(state, data) {
      state.processPageEdit = data;
    },
    updateHookPageEdit(state, data) {
      state.hookPageEdit = data;
    },
    updateModuleInfoEdit(state, data) {
      state.isModuleInfoEdit = data;
    },
  },
  actions: {
    /**
     * --
     * @param {Object} params 请求参数：appCode
     */
    getApis({}, { appCode }, config = {}) {
      const url = `${BACKEND_URL}/api/cloudapi/apps/${appCode}/apis/`;
      return http.get(url, config);
    },

    /**
     * --
     * @param {Object} params 请求参数：appCode
     */
    getAppPermissions({}, { appCode }, config = {}) {
      const url = `${BACKEND_URL}/api/cloudapi/apps/${appCode}/apis/permissions/app-permissions/`;
      return http.get(url, config);
    },

    /**
     * --
     * @param {Object} params
     */
    getApplyRecords({}, params, config = {}) {
      const requsetParams = Object.assign({}, params);
      delete requsetParams.appCode;
      const url = `${BACKEND_URL}/api/cloudapi/apps/${params.appCode}/apis/permissions/apply-records/?${json2Query(requsetParams)}`;
      return http.get(url, config);
    },

    /**
     * --
     * @param {Object} params 请求参数：appCode, recordId
     */
    getApplyRecordDetail({}, { appCode, recordId }, config = {}) {
      const url = `${BACKEND_URL}/api/cloudapi/apps/${appCode}/apis/permissions/apply-records/${recordId}/`;
      return http.get(url, config);
    },

    /**
     * --
     * @param {Object} params 请求参数：appCode, apiId
     */
    getAllowApplyByApi({}, { appCode, apiId }, config = {}) {
      const url = `${BACKEND_URL}/api/cloudapi/apps/${appCode}/apis/${apiId}/permissions/allow-apply-by-api/`;
      return http.get(url, config);
    },

    /** 网关申请 - 不支持跨网关
     * @param {Object} params 请求参数：appCode, apiId, data
     */
    apply({}, { appCode, apiId, data }, config = {}) {
      const url = `${BACKEND_URL}/api/cloudapi/apps/${appCode}/apis/${apiId}/permissions/apply/`;
      return http.post(url, data, config);
    },

    /**
     * 组件申请 - 不支持跨组件
     * @param {Object} params 请求参数：appCode, systemId, data
     */
    sysApply({}, { appCode, systemId, data }, config = {}) {
      const url = `${BACKEND_URL}/api/cloudapi/apps/${appCode}/esb/systems/${systemId}/permissions/apply/`;
      return http.post(url, data, config);
    },

    /** 网关续期 -支持跨网关
     * @param {Object} params 请求参数：appCode, data
     */
    renewal({}, { appCode, data }, config = {}) {
      const url = `${BACKEND_URL}/api/cloudapi/apps/${appCode}/apis/permissions/renew/`;
      return http.post(url, data, config);
    },

    /** 组件续期 -支持跨组件
     * @param {Object} params 请求参数：appCode, data
     */
    sysRenewal({}, { appCode, data }, config = {}) {
      const url = `${BACKEND_URL}/api/cloudapi/apps/${appCode}/esb/systems/permissions/renew/`;
      return http.post(url, data, config);
    },

    /**
     * --
     * @param {Object} params 请求参数：appCode, apiId
     */
    getResources({}, { appCode, apiId }, config = {}) {
      const url = `${BACKEND_URL}/api/cloudapi/apps/${appCode}/apis/${apiId}/permissions/resources/`;
      return http.get(url, config);
    },

    /**
     * --
     * @param {Object} params 请求参数：appCode
     */
    getSystems({}, { appCode }, config = {}) {
      const url = `${BACKEND_URL}/api/cloudapi/apps/${appCode}/esb/systems/`;
      return http.get(url, config);
    },

    /**
     * --
     * @param {Object} params 请求参数：appCode
     */
    getSysAppPermissions({}, { appCode }, config = {}) {
      const url = `${BACKEND_URL}/api/cloudapi/apps/${appCode}/esb/systems/permissions/app-permissions/`;
      return http.get(url, config);
    },

    /**
     * --
     * @param {Object} params
     */
    getSysApplyRecords({}, params, config = {}) {
      const requsetParams = Object.assign({}, params);
      delete requsetParams.appCode;
      const url = `${BACKEND_URL}/api/cloudapi/apps/${params.appCode}/esb/systems/permissions/apply-records/?${json2Query(requsetParams)}`;
      return http.get(url, config);
    },

    /**
     * --
     * @param {Object} params 请求参数：appCode, recordId
     */
    getSysApplyRecordDetail({}, { appCode, recordId }, config = {}) {
      const url = `${BACKEND_URL}/api/cloudapi/apps/${appCode}/esb/systems/permissions/apply-records/${recordId}/`;
      return http.get(url, config);
    },

    /**
     * --
     * @param {Object} params 请求参数：appCode, systemId
     */
    getComponents({}, { appCode, systemId }, config = {}) {
      const url = `${BACKEND_URL}/api/cloudapi/apps/${appCode}/esb/systems/${systemId}/permissions/components/`;
      return http.get(url, config);
    },

    /**
     * --
     * @param {Object} params 请求参数：data
     */
    createCloudApp({}, { data }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/cloud-native/`;
      return http.post(url, data, config);
    },

    /**
     * 获取新令牌
     * @param {string} appCode 应用id
     * @param {string} moduleId 环境id
     */
    getAccessToken({}, { appCode }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/oauth/token/prod/`;
      return http.get(url, config);
    },

    /**
     * 获取蓝鲸插件模板信息
     */
    getPluginTmpls() {
      const url = `${BACKEND_URL}/api/bkapps/plugin/tmpls/`;
      return http.get(url);
    },

    /**
     * MCP-获取 MCP Server 列表
     */
    getMcpServerList({}, { appCode }) {
      const url = `${BACKEND_URL}/api/cloudapi-v2/apps/${appCode}/inner/mcp-servers/`;
      return http.get(url);
    },

    /**
     * 申请 MCP Server 权限
     */
    applyMcpServerPermission({}, { appCode, data }) {
      const url = `${BACKEND_URL}/api/cloudapi-v2/apps/${appCode}/inner/mcp-servers/permissions/apply/`;
      return http.post(url, data);
    },

    /**
     * MCP-获取已申请权限列表
     */
    getMcpAppliedPermissions({}, { appCode }) {
      const url = `${BACKEND_URL}/api/cloudapi-v2/apps/${appCode}/inner/mcp-servers/permissions/`;
      return http.get(url);
    },

     /**
     * MCP-获取申请记录
     */
    getMcpServerApplyRecords({}, { appCode, ...requsetParams }) {
      const url = `${BACKEND_URL}/api/cloudapi-v2/apps/${appCode}/inner/mcp-servers/permissions/apply-records/?${json2Query(requsetParams)}`;
      return http.get(url);
    },
  },
};
