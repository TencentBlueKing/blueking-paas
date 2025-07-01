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
import i18n from '@/language/i18n';

/**
 * @file 平台管理导航 （platform）
 */
export default [
  {
    groupId: 'platform',
    name: 'platformOverview',
    label: i18n.t('概览'),
    iconfontName: 'overview1',
    matchRouters: ['platformOverview'],
    destRoute: {
      name: 'platformOverview',
    },
    sublist: [],
  },
  {
    groupId: 'platform',
    name: 'platformAppCluster',
    label: i18n.t('应用集群'),
    iconfontName: 'organization',
    matchRouters: ['platformAppCluster', 'clusterCreateEdit'],
    destRoute: {
      name: 'platformAppCluster',
    },
    sublist: [],
  },
  {
    groupId: 'platform',
    name: 'platformAddOns',
    label: i18n.t('增强服务'),
    iconfontName: 'diamond',
    matchRouters: ['platformAddOns'],
    destRoute: {
      name: 'platformAddOns',
    },
    sublist: [],
  },
  {
    groupId: 'operations',
    name: 'platformAppList',
    label: i18n.t('应用列表'),
    iconfontName: 'Application-list',
    matchRouters: ['platformAppList', 'platformAppDetails'],
    destRoute: {
      name: 'platformAppList',
    },
    sublist: [],
  },
  {
    groupId: 'config',
    name: 'repositoryConfig',
    label: i18n.t('代码库配置'),
    iconfontName: 'daimakupeizhi',
    matchRouters: ['repositoryConfig'],
    destRoute: {
      name: 'repositoryConfig',
    },
    sublist: [],
  },
  {
    groupId: 'config',
    name: 'templateConfig',
    label: i18n.t('模版配置'),
    iconfontName: 'mobanpeizhi',
    matchRouters: ['templateConfig'],
    destRoute: {
      name: 'templateConfig',
    },
    sublist: [],
  },
  {
    groupId: 'config',
    name: 'builtInEnvVariable',
    label: i18n.t('内置环境变量'),
    iconfontName: 'variable',
    matchRouters: ['builtInEnvVariable'],
    destRoute: {
      name: 'builtInEnvVariable',
    },
    sublist: [],
  },
  {
    groupId: 'user',
    name: 'platformUserManagement',
    label: i18n.t('用户管理'),
    iconfontName: 'user-line',
    matchRouters: ['platformUserManagement'],
    destRoute: {
      name: 'platformUserManagement',
    },
    sublist: [],
  },
  {
    groupId: 'user',
    name: 'platformOperationAudit',
    label: i18n.t('操作审计'),
    iconfontName: 'caozuoshenji',
    matchRouters: ['platformOperationAudit'],
    destRoute: {
      name: 'platformOperationAudit',
    },
    sublist: [],
  },
];
