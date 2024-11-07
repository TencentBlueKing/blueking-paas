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
  沙箱开发
*/
import http from '@/api';

export default {
  namespaced: true,
  state: {},
  getters: {},
  mutations: {},
  actions: {
    /**
     * 创建沙箱
     */
    createSandbox({}, { appCode, moduleId, data }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/user/dev_sandbox_with_code_editor/`;
      return http.post(url, data, config);
    },
    /**
     * 获取沙箱列表
     */
    getSandboxList({}, { appCode }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/user/dev_sandbox_with_code_editors/lists/`;
      return http.get(url, config);
    },
    /**
     * 销毁沙箱
     */
    destroySandbox({}, { appCode, moduleId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/user/dev_sandbox_with_code_editor/`;
      return http.delete(url, config);
    },
    /**
     * 获取沙箱界面数据
     */
    getSandboxWithCodeEditor({}, { appCode, moduleId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/user/dev_sandbox_with_code_editor/`;
      return http.get(url, config);
    },
    /**
     * 获取沙箱环境密码
     */
    getSandboxPassword({}, { appCode, moduleId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/user/dev_sandbox_password/`;
      return http.get(url, config);
    },
    /**
     * 获取沙箱增强服务信息
     */
    getEnhancedServices({}, { appCode, moduleId }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/envs/stag/services/attachments/`;
      return http.get(url, config);
    },
    /**
     * 新建沙箱前置检查
     */
    createSandboxPreDeployCheck({}, { appCode }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/user/dev_sandbox_with_code_editors/pre_deploy_check/`;
      return http.get(url, config);
    },
  },
};
