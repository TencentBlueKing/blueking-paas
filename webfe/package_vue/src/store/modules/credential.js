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
    创建app
*/
import http from '@/api';

export default {
  namespaced: true,
  state: {},
  getters: {},
  mutations: {},
  actions: {
    /*
      获取镜像凭证列表
    */
    getImageCredentialList ({ commit, state }, { appCode }, config = {}) {
      const url = `${BACKEND_URL}/svc_workloads/api/credentials/applications/${appCode}/image_credentials/`;
      return http.get(url, config);
    },

    /*
      新增镜像凭证
    */
    addImageCredential ({ commit, state }, { appCode, data }, config = {}) {
      const url = `${BACKEND_URL}/svc_workloads/api/credentials/applications/${appCode}/image_credentials/`;
      return http.post(url, data, config);
    },

    /*
      更新镜像凭证
    */
    updateImageCredential ({ commit, state }, { appCode, crdlName, data }, config = {}) {
      const url = `${BACKEND_URL}/svc_workloads/api/credentials/applications/${appCode}/image_credentials/${crdlName}`;
      return http.put(url, data, config);
    },

    /*
      删除单个镜像凭证
    */
    deleteImageCredential ({ commit, state }, { appCode, crdlName }, config = {}) {
      const url = `${BACKEND_URL}/svc_workloads/api/credentials/applications/${appCode}/image_credentials/${crdlName}`;
      return http.delete(url, config);
    }
  }
};
