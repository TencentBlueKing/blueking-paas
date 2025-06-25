// 基本信息
export const BASE_INFO_FORM_CONFIG = [
  {
    property: 'name',
    label: '模板名称',
    type: 'input',
  },
  {
    property: 'type',
    label: '模板类型',
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
    property: 'is_hidden',
    label: '是否展示',
    type: 'switcher',
  },
];

// 模板信息（插件模块）
export const PLUGIN_FORM_CONFIG = [
  {
    property: 'repo_url',
    label: '代码仓库地址',
    type: 'input',
  },
  {
    property: 'source_dir',
    label: '代码目录',
    type: 'input',
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

