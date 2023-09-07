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

export const APP_TYPES = {
  dj18_hello_world: 'backend',
  dj18_with_auth: 'web',
  dj18_sample_with_auth: 'web',
  laveral51_with_auth: 'web',
  laveral51_sample_with_auth: 'web',
  go_gin_hello_world: 'backend',
  nodejs_express_hello_world: 'backend',
};
export const APP_LANGUAGES_IMAGE = {
  Python: {
    normal: '/static/images/python-1.png',
    hover: '/static/images/python.png',
  },
  PHP: {
    normal: '/static/images/php.png',
    hover: '/static/images/php-1.png',
  },
  Go: {
    normal: '/static/images/golang.png',
    hover: '/static/images/golang-1.png',
  },
  NodeJS: {
    normal: '/static/images/nodejs.png',
    hover: '/static/images/nodejs-1.png',
  },
};

export const DEFAULT_APP_SOURCE_CONTROL_TYPES = [
  {
    value: 'bk_svn',
    name: '蓝鲸 SVN 服务',
    description: '（蓝鲸平台提供的源码托管服务）',
  },
];

export const APP_ROLE_NAMES = {
  administrator: '管理员',
  developer: '开发者',
  operator: '运营者',
};

export const DEFAULR_LANG_NAME = {
  Python: 'Python开发框架',
  Go: 'Golang开发框架',
  NodeJS: 'NodeJS开发框架',
};

export const PLUGIN_STATUS = {
  'waiting-approval': '创建审批中',
  'approval-failed': '创建审批失败',
  developing: '开发中',
  releasing: '发布中',
  released: '已发布',
  archived: '已下架',
};

export const PLUGIN_VERSION_STATUS = {
  successful: '成功',
  failed: '失败',
  pending: '发布中',
  initial: '发布中',
  interrupted: '已中断',
};

/**
 * 自定义工具栏
 */
export const TOOLBAR_OPTIONS = [
  ['bold', 'italic', 'underline', 'strike',
    { color: [] },
    { background: [] },
    { align: ['', 'center', 'right', 'justify'] },
    'blockquote',
    { indent: '-1' }, { indent: '+1' },
    { list: 'ordered' },
    { list: 'bullet' },
    'link',
    'image',
    'code-block',
  ],
];

export const ENV_ENUM = {
  prod: '生产环境',
  stag: '预发布环境',
};

export const RESQUOTADATA = ['default', '1C512M', '2C1G', '2C2G', '4C1G', '4C2G'];
export const PLUGIN_ITSM_APPLY = {
  plugin_id: '插件标识',
  plugin_name: '插件名称',
  language: '开发语言',
  repository: '代码库',
  version: '版本号',
  comment: '版本日志',
  source_version_name: '代码分支',
  category: '分类',
  introduction: '简介',
  description: '详情描述',
};

export const PLUGIN_ITSM_LADING = {
  title: '标题',
  creator: '提单人',
};

export const TAG_MAP = {
  with_version: '{分支/标签}',
  with_build_time: '构建时间',
  with_commit_id: 'commitID',
};

export const DEPLOY_STATUS = {
  successful: '成功',
  failed: '失败',
  interrupted: '中断'
};
