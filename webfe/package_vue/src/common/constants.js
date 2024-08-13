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


/**
 * 正式版本状态
 */
export const PLUGIN_VERSION_STATUS = {
  successful: '成功',
  failed: '失败',
  pending: '等待',
  initial: '初始化',
  interrupted: '已中断',
};

/**
 * 测试版状态
 */
export const PLUGIN_TEST_VERSION_STATUS = {
  successful: '测试成功',
  failed: '测试失败',
  pending: '测试中',
  initial: '初始化',
  interrupted: '已中断',
};

/**
 * 自定义工具栏
 */
export const TOOLBAR_OPTIONS = [
  [
    'bold',
    'italic',
    'underline',
    'strike',
    { color: [] },
    { background: [] },
    { align: ['', 'center', 'right', 'justify'] },
    'blockquote',
    { indent: '-1' },
    { indent: '+1' },
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
  interrupted: '中断',
};

export const ENV_OVERLAY = {
  prod: {
    environment_name: 'prod',
    plan_name: 'default',
    target_replicas: 1,
    autoscaling: false,
    scaling_config: {
      min_replicas: 1,
      max_replicas: 2,
      metrics: [
        {
          type: 'Resource',
          metric: 'cpuUtilization',
          value: '85%',
        },
      ],
      policy: 'default',
    },
  },
  stag: {
    environment_name: 'stag',
    plan_name: 'default',
    target_replicas: 1,
    autoscaling: false,
    scaling_config: {
      min_replicas: 1,
      max_replicas: 2,
      metrics: [
        {
          type: 'Resource',
          metric: 'cpuUtilization',
          value: '85%',
        },
      ],
      policy: 'default',
    },
  },
};

export const THRESHOLD_MAP = {
  gte: '>=',
  eq: '=',
  lt: '<',
  lte: '<=',
  gt: '>',
  ne: '!=',
};

export const LEVEL_MAP = ['致命', '预警', '提醒'];

export const TE_MIRROR_EXAMPLE = 'mirrors.tencent.com/bkpaas/django-helloworld';

export const APPROVALSTATUS = {
  pending: 'approval',
  initial: 'approval',
  successful: 'successful',
  failed: 'failed',
  interrupted: 'interrupted',
};

export const STATUSBARDATA = {
  approval: {
    title: '等待审批',
    type: 'warning',
  },
  successful: {
    title: '审批通过',
    type: 'success',
  },
  failed: {
    title: '审批不通过',
    type: 'failed',
  },
  interrupted: {
    title: '已撤销提单',
    type: 'interrupted',
  },
};

/**
 * 插件新建版本对应阶段
 */
export const PLUGIN_VERSION_MAP = {
  pipeline: 'build',
  deployAPI: 'deploy',
  subpage: 'test',
  itsm: 'itsm',
};

/**
 * 版本号类型
 */
export const VERSION_NUMBER_TYPE = {
  major: '重大版本',
  minor: '次版本',
  patch: '修正版本',
};

/**
 * 持久存储容量映射
 */
export const PERSISTENT_STORAGE_SIZE_MAP = {
  '1Gi': '1GB',
  '2Gi': '2GB',
  '4Gi': '4GB',
};

/**
 * 应用类型
 */
export const PAAS_APP_TYPE = {
  default: '普通应用',
  cloud_native: '云原生应用',
  engineless_app: '外链应用',
};

export const CIRCLED_NUMBERS = [
  '①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩',
  '⑪', '⑫', '⑬', '⑭', '⑮', '⑯', '⑰', '⑱', '⑲', '⑳',
];

/**
 * Codecc 版本发布状态
 */
export const CODECC_RELEASE_STATUS = {
  pending: '灰度中',
  successful: '已全量发布',
  interrupted: '发布异常',
  failed: '发布异常',
};
