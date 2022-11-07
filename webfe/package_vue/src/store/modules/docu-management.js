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

/**
 * 文档管理相关API
 */
import http from '@/api';

export default {
    namespaced: true,
    state: {},
    mutations: {},
    actions: {
        /**
         * 获取当前应用下，所有的文档模板及实例
         *
         * @param {Object} params
         */
        getDocumentInstance ({ commit, state }, params) {
            const url = `${BACKEND_URL}/api/bkapps/applications/${params.appCode}/document/instance/`;
            return http.get(url);
        },

        /**
         * 实例不存在时，更新文档实例
         *
         * @param {Object} params
         */
        updateDocumentInstance ({ commit, state }, params) {
            const requestParams = Object.assign({}, params);
            delete requestParams.appCode;
            const url = `${BACKEND_URL}/api/bkapps/applications/${params.appCode}/document/instance/`;
            return http.post(url, requestParams);
        },

        /**
         * 实例存在时，更新文档实例
         *
         * @param {Object} params
         */
        updateDocumentInstanceByExist ({ commit, state }, params) {
            const requestParams = Object.assign({}, params);
            delete requestParams.appCode;
            delete requestParams.id;
            const url = `${BACKEND_URL}/api/bkapps/applications/${params.appCode}/document/instance/${params.id}/`;
            return http.put(url, requestParams);
        }
    }
};
