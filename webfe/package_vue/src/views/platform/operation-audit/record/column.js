// 平台管理操作记录
export const platformColumns = [
  {
    label: '操作对象',
    prop: 'target',
  },
  {
    label: '操作类型',
    prop: 'operation',
  },
  {
    label: '对象属性',
    prop: 'attribute',
  },
  {
    label: '状态',
    prop: 'status',
  },
  {
    label: '操作人',
    prop: 'operator',
  },
  {
    label: '操作时间',
    prop: 'operated_at',
  },
];

// 应用操作记录
export const appColumns = [
  {
    label: '操作对象',
    prop: 'target',
  },
  {
    label: '操作类型',
    prop: 'operation',
  },
  {
    label: '应用 ID',
    prop: 'app_code',
  },
  {
    label: '模块',
    prop: 'module_name',
  },
  {
    label: '环境',
    prop: 'environment',
  },
  {
    label: '状态',
    prop: 'status',
  },
  {
    label: '操作人',
    prop: 'operator',
  },
  {
    label: '操作时间',
    prop: 'operated_at',
  },
];
