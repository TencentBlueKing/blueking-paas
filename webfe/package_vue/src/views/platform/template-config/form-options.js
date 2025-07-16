import i18n from '@/language/i18n.js';

// 基本信息
export const BASE_INFO_FORM_CONFIG = [
  {
    property: 'name',
    label: '模版名称',
    type: 'input',
    placeholder: '只能由字符 [a-zA-Z0-9-_] 组成',
    rules: [
      {
        required: true,
        message: i18n.t('必填项'),
        trigger: 'blur',
      },
      {
        regex: /^[a-zA-Z0-9\-_]+$/,
        message: i18n.t('以英文字母、数字或下划线(_)组成'),
        trigger: 'blur',
      },
    ],
  },
  {
    property: 'type',
    label: '模版类型',
    type: 'select',
    metadataKey: 'template_types',
  },
  {
    property: 'render_method',
    label: '渲染方式',
    type: 'select',
    metadataKey: 'render_methods',
  },
  {
    property: 'display_name_zh_cn',
    label: '展示名称（中）',
    type: 'input',
  },
  {
    property: 'display_name_en',
    label: '展示名称（英）',
    type: 'input',
  },
  {
    property: 'description_zh_cn',
    label: '描述（中）',
    type: 'input',
  },
  {
    property: 'description_en',
    label: '描述（英）',
    type: 'input',
  },
  {
    property: 'language',
    label: '开发语言',
    type: 'select',
    metadataKey: 'application_types',
  },
  {
    property: 'is_display',
    label: '是否展示',
    type: 'switcher',
    desc: '用户在创建应用/模块时仅能使用未隐藏的模板，但现有应用仍可下载已隐藏的模板。',
  },
];

// 模板信息（插件模块）
export const PLUGIN_FORM_CONFIG = [
  {
    property: 'repo_url',
    label: '代码仓库地址',
    type: 'input',
    placeholder: '请输入代码仓库地址',
  },
  {
    property: 'source_dir',
    label: '代码目录',
    type: 'input',
    placeholder: '请输入代码所在目录，不填则为根目录',
  },
  {
    property: 'repo_type',
    label: '代码仓库类型',
    type: 'select',
    metadataKey: 'repo_types',
  },
];

// 配置信息
export const CONFIG_INFO_FORM_CONFIG = [
  {
    property: 'preset_services_config',
    label: '预设增强服务配置',
    type: 'json',
    ref: 'servicesEditor',
  },
  {
    property: 'required_buildpacks',
    label: '必须的构建工具',
    type: 'json',
    ref: 'buildEditor',
  },
  {
    property: 'processes',
    label: '进程配置',
    type: 'json',
    ref: 'processesEditor',
  },
];
