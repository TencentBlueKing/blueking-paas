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
 * 平台管理-配置管理
 */
import http from '@/api';

export default {
  namespaced: true,
  actions: {
    /**
     * 获取内置环境变量
     */
    getBuiltinConfigVars() {
      const url = `${BACKEND_URL}/api/plat_mgt/builtin_config_vars/`;
      return http.get(url);
    },
    /**
     * 新建内置环境变量
     */
    addBuiltinConfigVars({}, { params }) {
      const url = `${BACKEND_URL}/api/plat_mgt/builtin_config_vars/`;
      return http.post(url, params);
    },
    /**
     * 编辑内置环境变量
     */
    updateBuiltinConfigVars({}, { id, params }) {
      const url = `${BACKEND_URL}/api/plat_mgt/builtin_config_vars/${id}/`;
      return http.put(url, params);
    },
    /**
     * 删除内置环境变量
     */
    deleteBuiltinConfigVars({}, { id }) {
      const url = `${BACKEND_URL}/api/plat_mgt/builtin_config_vars/${id}/`;
      return http.delete(url);
    },
    /**
     * 代码库配置-获取代码库列表
     */
    getSourceTypeSpec() {
      const url = `${BACKEND_URL}/api/plat_mgt/sourcectl/source_type_spec/`;
      return http.get(url);
    },
    /**
     * 代码库配置-获取配置类下拉列表
     */
    getSpecClsChoices() {
      const url = `${BACKEND_URL}/api/plat_mgt/sourcectl/spec_cls_choices/`;
      return http.get(url);
    },
     /**
     * 代码库配置-获取表单默认配置项
     */
    getDefaultConfigsTemplates() {
      const url = `${BACKEND_URL}/api/plat_mgt/sourcectl/source_type_spec/default_configs_templates/`;
      return http.get(url);
    },
    /**
     * 代码库配置-获取代码库配置详情
     */
    getRepositoryDetail({}, { id }) {
      const url = `${BACKEND_URL}/api/plat_mgt/sourcectl/source_type_spec/${id}/`;
      return http.get(url);
    },
    /**
     * 代码库配置-创建代码库配置
     */
    createRepositoryConfig({}, { data }) {
      const url = `${BACKEND_URL}/api/plat_mgt/sourcectl/source_type_spec/`;
      return http.post(url, data);
    },
    /**
     * 代码库配置-修改代码库配置
     */
    updateRepositoryConfig({}, { id, data }) {
      const url = `${BACKEND_URL}/api/plat_mgt/sourcectl/source_type_spec/${id}/`;
      return http.put(url, data);
    },
    /**
     * 代码库配置-删除代码库配置
     */
    deleteRepositoryConfig({}, { id }) {
      const url = `${BACKEND_URL}/api/plat_mgt/sourcectl/source_type_spec/${id}/`;
      return http.delete(url);
    },
  },
};
