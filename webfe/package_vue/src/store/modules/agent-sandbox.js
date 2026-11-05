/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) Tencent. All rights reserved.
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

import http from '@/api';

// Components discard stale results when the application changes. Let requests settle
// so that creating a key can always remove the response from the shared HTTP cache.
const requestConfig = {
  fromCache: false,
  cancelPrevious: false,
  cancelWhenRouteChange: false,
};

function consoleUrl(appCode) {
  return `${BACKEND_URL}/api/bkapps/applications/${encodeURIComponent(appCode)}/agent_sandbox/e2b/`;
}

export default {
  namespaced: true,
  actions: {
    listSandboxes({}, { appCode, templateId = '' }) {
      return http.get(`${consoleUrl(appCode)}sandboxes/`, {}, {
        ...requestConfig,
        params: templateId ? { template_id: templateId } : {},
      });
    },
    destroySandbox({}, { appCode, sandboxId }) {
      return http.delete(`${consoleUrl(appCode)}sandboxes/${encodeURIComponent(sandboxId)}`, {}, requestConfig);
    },
    listTemplates({}, { appCode }) {
      return http.get(`${consoleUrl(appCode)}templates/`, {}, requestConfig);
    },
    getTemplate({}, { appCode, templateId }) {
      return http.get(`${consoleUrl(appCode)}templates/${encodeURIComponent(templateId)}`, {}, requestConfig);
    },
    listApiKeys({}, { appCode }) {
      return http.get(`${consoleUrl(appCode)}api_keys/`, {}, requestConfig);
    },
    async createApiKey({}, { appCode, name }) {
      const url = `${consoleUrl(appCode)}api_keys/`;
      const requestId = `post_${url}`;
      try {
        return await http.post(url, { name }, { ...requestConfig, requestId });
      } finally {
        // fromCache:false only disables reads; the shared client still caches POST responses.
        await http.cancelCache(requestId);
      }
    },
    revokeApiKey({}, { appCode, uuid }) {
      return http.delete(`${consoleUrl(appCode)}api_keys/${encodeURIComponent(uuid)}`, {}, requestConfig);
    },
  },
};
