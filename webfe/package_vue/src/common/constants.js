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
  Python: 'Python 开发框架',
  Go: 'Go 开发框架',
  NodeJS: 'NodeJS 开发框架',
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
  gray_approval_in_progress: '灰度发布审批中',
  in_gray: '灰度中',
  gray_approval_failed: '灰度审批失败',
  full_approval_in_progress: '全量发布审批中',
  fully_released: '已全量发布',
  full_approval_failed: '全量发布审批失败',
  rolled_back: '已回滚',
  interrupted: '已终止',
};

/**
 * 操作记录-操作对象
 */
export const APP_OPERATION_TARGET = {
  app: '应用',
  module: '模块',
  process: '进程',
  env_var: '环境变量',
  addon: '增强服务',
  cloud_api: '云 API 权限',
  secret: '密钥',
  app_domain: '访问地址',
  app_member: '应用成员',
  build_config: '构建配置',
  volume_mount: '挂载卷',
  service_discovery: '服务发现',
  domain_resolution: '域名解析',
  deploy_restriction: '部署限制',
  exit_ip: '出口 IP',
  access_control: '用户限制',
  access_token: '访问令牌',
};

/**
 * 操作记录-操作类型
 */
export const APP_OPERATION = {
  create: '新建',
  delete: '删除',
  modify: '修改',
  refresh: '刷新',
  create_app: '创建应用',
  online_to_market: '发布到应用市场',
  offline_from_market: '从应用市场下架',
  modify_market_info: '完善应用市场配置',
  modify_market_url: '修改应用市场访问地址',
  modify_basic_info: '修改基本信息',
  start: '启动',
  stop: '停止',
  scale: '扩缩容',
  enable: '启用',
  disable: '停用',
  apply: '申请',
  renew: '续期',
  deploy: '部署',
  offline: '下架',
  switch: '切换资源方案',
  modify_user_feature_flag: '修改用户特性',
  switch_default_cluster: '切换默认集群',
  bind_cluster: '切换绑定集群',
  modify_log_config: '日志采集管理',
  provision_instance: '分配增强服务实例',
  recycle_resource: '回收增强服务实例',
};

/**
 * 操作记录-状态
 */
export const APP_RESULT_CODE = {
  0: '成功',
  1: '执行中',
  '-1': '失败',
  '-2': '中断',
};

/**
 * 应用详情-应用状态
 */
export const APP_DATAILS_STATUS = {
  none: '健康',
  ownerless: '无主',
  idle: '闲置',
  unvisited: '无用户访问',
  maintainless: '缺少维护',
  undeploy: '未部署',
  misconfigured: '配置不当',
};

/**
 * 插件-操作记录-操作对象
 */
export const PLUGIN_SUBJECT = {
  plugin: '插件',
  test_version: '测试版本',
  version: '版本',
  basic_info: '基本信息',
  logo: 'logo',
  market_info: '市场信息',
  config_info: '配置信息',
  visible_range: '可见范围',
  publisher: '发布者',
  release_strategy: '发布策略',
};

/**
 * 插件-操作记录-操作类型
 */
export const PLUGIN_ACTION = {
  create: '创建',
  add: '新建',
  re_release: '重新发布',
  terminate: '终止发布',
  modify: '修改',
  delete: '删除',
  archive: '下架',
  reactivate: '重新上架',
  rollback: '回滚',
};

/**
 * 租户模式
 */
export const APP_TENANT_MODE = {
  single: '单租户',
  global: '全租户',
};

/**
* 平台管理-组件状态
*/
export const COMPONENT_STATUS = {
  not_installed: '未安装',
  installing: '安装中',
  installed: '已安装',
  installation_failed: '安装失败',
};
