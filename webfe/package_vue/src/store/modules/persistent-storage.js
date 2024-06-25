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

/**
 * 持久化存储
 */
import http from '@/api';

export default {
  namespaced: true,
  state: {},
  getters: {},
  mutations: {},
  actions: {
    /**
     * 获取持久存储数据
     * @param {Object} params appCode、sourceType
     */
    getPersistentStorageList({}, { appCode, sourceType }) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/mres/mount_sources/?source_type=${sourceType}`;
      return http.get(url);
    },

    /**
     * 获取持久存储功能性开关
     * @param {Object} params appCode、sourceType
     */
    getpersistentStorageFeature({}, { appCode }) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/mres/persistent_storage_feature/`;
      return http.get(url);
    },


    /**
     * 新增持久存储
     * @param {Object} params appCode、data
     */
    createPersistentStorage({}, { appCode, data }) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/mres/mount_sources/`;
      return http.post(url, data);
    },

    /**
     * 删除持久存储
     * @param {Object} params appCode、sourceType、sourceName
     */
    deletePersistentStorage({}, { appCode, sourceType, sourceName }) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/mres/mount_sources/?source_type=${sourceType}&source_name=${sourceName}`;
      return http.delete(url);
    },

    /**
     * 集群是否支持持久存储
     * @param {Object} params appCode
     */
    getClusterPersistentStorageFeature({}, { appCode }) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/mres/storage_class/`;
      return http.get(url);
    },
  },
};
