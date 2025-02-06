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
 * 管理当前 app 包版本相关的属性
 */
import http from '@/api';
import { json2Query } from '@/common/tools';

const state = {};

const getters = {};

const mutations = {};

// actions
const actions = {
  /**
   * 获取应用包版本列表
   * @param {Object} params 请求参数：appCode, moduleId, params
   */
  getAppPackageList({}, { isLesscodeApp, appCode, moduleId, params }, config = {}) {
    const modules = isLesscodeApp ? `/modules/${moduleId}` : '';
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}${modules}/source_package/?${json2Query(params)}`;
    return http.get(url, config);
  },

  /**
   * 提交包
   * @param {Object} params 请求参数：appCode, moduleId, signature
   */
  commitPackage({}, { appCode, signature }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/source_package/commit/${signature}/`;
    return http.post(url, {}, config);
  },

  /**
   * 创建smart应用
   * @param {Object} params 请求参数：appCode, moduleId, signature
   */
  createSmartApp({}, { params }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/s-mart/confirm/`;
    return http.post(url, params, config);
  },
};

export default {
  namespaced: true,
  state,
  getters,
  mutations,
  actions,
};
