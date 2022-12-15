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
    cloudAppData: {}
  },
  getters: {},
  mutations: {
    updateCloudAppData (state, data) {
      state.cloudAppData = data;
    }
  },
  actions: {
    /**
         * --
         * @param {Object} params 请求参数：appCode
         */
    getApis ({ commit, state }, { appCode }, config = {}) {
      const url = `${BACKEND_URL}/api/cloudapi/apps/${appCode}/apis/`;
      return http.get(url, config);
    },

    /**
         * --
         * @param {Object} params 请求参数：appCode
         */
    getAppPermissions ({ commit, state }, { appCode }, config = {}) {
      const url = `${BACKEND_URL}/api/cloudapi/apps/${appCode}/apis/permissions/app-permissions/`;
      return http.get(url, config);
    },

    /**
         * --
         * @param {Object} params
         */
    getApplyRecords ({ commit, state }, params, config = {}) {
      const requsetParams = Object.assign({}, params);
      delete requsetParams.appCode;
      const url = `${BACKEND_URL}/api/cloudapi/apps/${params.appCode}/apis/permissions/apply-records/?${json2Query(requsetParams)}`;
      return http.get(url, config);
    },

    /**
         * --
         * @param {Object} params 请求参数：appCode, recordId
         */
    getApplyRecordDetail ({ commit, state }, { appCode, recordId }, config = {}) {
      const url = `${BACKEND_URL}/api/cloudapi/apps/${appCode}/apis/permissions/apply-records/${recordId}/`;
      return http.get(url, config);
    },

    /**
         * --
         * @param {Object} params 请求参数：appCode, apiId
         */
    getAllowApplyByApi ({ commit, state }, { appCode, apiId }, config = {}) {
      const url = `${BACKEND_URL}/api/cloudapi/apps/${appCode}/apis/${apiId}/permissions/allow-apply-by-api/`;
      return http.get(url, config);
    },

    /**
         * --
         * @param {Object} params 请求参数：appCode, apiId, data
         */
    apply ({ commit, state }, { appCode, apiId, data }, config = {}) {
      const url = `${BACKEND_URL}/api/cloudapi/apps/${appCode}/apis/${apiId}/permissions/apply/`;
      return http.post(url, data, config);
    },

    /**
         * --
         * @param {Object} params 请求参数：appCode, data
         */
    renewal ({ commit, state }, { appCode, data }, config = {}) {
      const url = `${BACKEND_URL}/api/cloudapi/apps/${appCode}/apis/permissions/renew/`;
      return http.post(url, data, config);
    },

    /**
         * --
         * @param {Object} params 请求参数：appCode, apiId
         */
    getResources ({ commit, state }, { appCode, apiId }, config = {}) {
      const url = `${BACKEND_URL}/api/cloudapi/apps/${appCode}/apis/${apiId}/permissions/resources/`;
      return http.get(url, config);
    },

    /**
         * --
         * @param {Object} params 请求参数：appCode
         */
    getSystems ({ commit, state }, { appCode }, config = {}) {
      const url = `${BACKEND_URL}/api/cloudapi/apps/${appCode}/esb/systems/`;
      return http.get(url, config);
    },

    /**
         * --
         * @param {Object} params 请求参数：appCode
         */
    getSysAppPermissions ({ commit, state }, { appCode }, config = {}) {
      const url = `${BACKEND_URL}/api/cloudapi/apps/${appCode}/esb/systems/permissions/app-permissions/`;
      return http.get(url, config);
    },

    /**
         * --
         * @param {Object} params
         */
    getSysApplyRecords ({ commit, state }, params, config = {}) {
      const requsetParams = Object.assign({}, params);
      delete requsetParams.appCode;
      const url = `${BACKEND_URL}/api/cloudapi/apps/${params.appCode}/esb/systems/permissions/apply-records/?${json2Query(requsetParams)}`;
      return http.get(url, config);
    },

    /**
         * --
         * @param {Object} params 请求参数：appCode, recordId
         */
    getSysApplyRecordDetail ({ commit, state }, { appCode, recordId }, config = {}) {
      const url = `${BACKEND_URL}/api/cloudapi/apps/${appCode}/esb/systems/permissions/apply-records/${recordId}/`;
      return http.get(url, config);
    },

    /**
         * --
         * @param {Object} params 请求参数：appCode, systemId, data
         */
    sysApply ({ commit, state }, { appCode, systemId, data }, config = {}) {
      const url = `${BACKEND_URL}/api/cloudapi/apps/${appCode}/esb/systems/${systemId}/permissions/apply/`;
      return http.post(url, data, config);
    },

    /**
         * --
         * @param {Object} params 请求参数：appCode, data
         */
    sysRenewal ({ commit, state }, { appCode, data }, config = {}) {
      const url = `${BACKEND_URL}/api/cloudapi/apps/${appCode}/esb/systems/permissions/renew/`;
      return http.post(url, data, config);
    },

    /**
         * --
         * @param {Object} params 请求参数：appCode, systemId
         */
    getComponents ({ commit, state }, { appCode, systemId }, config = {}) {
      const url = `${BACKEND_URL}/api/cloudapi/apps/${appCode}/esb/systems/${systemId}/permissions/components/`;
      return http.get(url, config);
    }
  }
};
