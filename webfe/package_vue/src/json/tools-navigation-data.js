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
 * @file 工具导航
 */
export default [
  {
    groupId: 'devTools',
    name: 'serviceCode',
    label: i18n.t('代码库管理'),
    iconfontName: 'daimaku',
    matchRouters: ['serviceCode'],
    destRoute: {
      name: 'serviceCode',
    },
    sublist: [],
  },
  {
    groupId: 'devTools',
    name: 'descriptionFileConversion',
    label: i18n.t('应用描述文件转换'),
    iconfontName: 'wenjianzhuanhuan',
    matchRouters: ['descriptionFileConversion'],
    destRoute: {
      name: 'descriptionFileConversion',
    },
    sublist: [],
  },
  {
    groupId: 'devTools',
    name: 'smartBuildTool',
    label: i18n.t('S-mart 打包工具'),
    iconfontName: 'storehouse',
    matchRouters: ['smartBuildTool'],
    destRoute: {
      name: 'smartBuildTool',
    },
    sublist: [],
  },
  {
    groupId: 'serve',
    name: 'serviceAPIGateway',
    label: i18n.t('API 网关'),
    iconfontName: 'cloudapi',
    matchRouters: ['serviceAPIGateway'],
    destRoute: {
      name: 'serviceAPIGateway',
    },
    sublist: [],
  },
  {
    groupId: 'serve',
    name: 'serviceFramework',
    label: i18n.t('开发框架'),
    iconfontName: 'kaifakuangjia',
    matchRouters: ['serviceFramework'],
    destRoute: {
      name: 'serviceFramework',
    },
    sublist: [],
  },
  {
    groupId: 'serve',
    name: 'serviceMagicBox',
    label: i18n.t('前端组件库'),
    iconfontName: 'qianduanzujianku',
    matchRouters: ['serviceMagicBox'],
    destRoute: {
      name: 'serviceMagicBox',
    },
    sublist: [],
  },
  {
    groupId: 'serve',
    name: 'serviceLesscode',
    label: i18n.t('运维开发工具'),
    iconfontName: 'yunweikaifa',
    matchRouters: ['serviceLesscode'],
    destRoute: {
      name: 'serviceLesscode',
    },
    sublist: [],
  },
  {
    groupId: 'serve',
    name: 'workflow',
    label: i18n.t('流程引擎'),
    iconfontName: 'liuchengfuwu',
    matchRouters: ['serviceBamboo'],
    destRoute: {
      name: 'serviceBamboo',
    },
    sublist: [],
  },
  {
    groupId: 'serve',
    name: 'appServices',
    label: i18n.t('增强服务'),
    iconfontName: 'diamond',
    sublist: [
      {
        groupId: 'serve',
        name: i18n.t('数据存储'),
        matchRouters: ['serviceVas', 'serviceInnerPage'],
        destRoute: {
          name: 'serviceVas',
          params: {
            category_id: '1',
          },
        },
      },
      {
        groupId: 'serve',
        name: i18n.t('健康监测'),
        matchRouters: ['serviceVas', 'serviceInnerPage'],
        destRoute: {
          name: 'serviceVas',
          params: {
            category_id: '2',
          },
        },
      },
    ],
  },
];
