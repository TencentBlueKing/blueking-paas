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

// 平台管理
export default {
  平台管理: '平台管理',
  服务接入: '服务接入',
  应用集群: '应用集群',
  集群配置: '集群配置',
  集群列表: '集群列表',
  未配置: '未配置',
  已配置: '已配置',
  搜索租户: '搜索租户',
  租户: '租户',
  集群: '集群',
  配置: '配置',
  集群分配: '集群分配',
  '集群（预发布环境）': '集群（预发布环境）',
  '集群（生产环境）': '集群（生产环境）',
  '未配置，应用无法部署': '未配置，应用无法部署',
  前往添加: '前往添加',
  暂无集群可供分配: '暂无集群可供分配',
  '请先在 [集群列表] 添加集群，方可分配集群。': '请先在 [集群列表] 添加集群，方可分配集群。',
  分配方式: '分配方式',
  统一分配: '统一分配',
  按规则分配: '按规则分配',
  请选择集群: '请选择集群',
  '集群分配成功！': '集群分配成功！',
  '如果配置多个集群，开发者在创建应用时需要选择一个，未选择时，使用默认（第一个）集群。': '如果配置多个集群，开发者在创建应用时需要选择一个，未选择时，使用默认（第一个）集群。',
  '可选集群({n})': '可选集群({n})',
  '已选集群({n})': '已选集群({n})',
  按环境分配: '按环境分配',
  选择全部: '选择全部',
  暂无已选集群: '暂无已选集群',
  添加规则: '添加规则',
  '若执行集群扩缩容操作，请及时执行 “同步节点” 操作来更新集群节点状态。': '若执行集群扩缩容操作，请及时执行 “同步节点” 操作来更新集群节点状态。',
  '搜索集群名称、集群ID': '搜索集群名称、集群ID',
  集群视角: '集群视角',
  租户视角: '租户视角',
  集群名称: '集群名称',
  可用租户: '可用租户',
  特性: '特性',
  节点: '节点',
  同步节点: '同步节点',
  '确认同步节点？': '确认同步节点？',
  '同步集群节点到开发者中心，以便应用开启出口 IP 时能绑定到集群所有节点上。': '同步集群节点到开发者中心，以便应用开启出口 IP 时能绑定到集群所有节点上。',
  无法删除集群: '无法删除集群',
  '集群（{n}）正在被以下租户、应用使用，无法删除': '集群（{n}）正在被以下租户、应用使用，无法删除',
  被: '被',
  等: '等',
  '个租户使用，请先在集群配置页面，解除租户与集群的分配关系。': '个租户使用，请先在集群配置页面，解除租户与集群的分配关系。',
  'Bound-by': '被',
  个应用模块绑定: '个应用模块绑定',
  '确认删除集群？': '确认删除集群？',
  '删除集群仅会解除与开发者中心的托管关系，集群中已部署的应用和组件仍然可用。如不再需要，请到集群中手动进行清理。': '删除集群仅会解除与开发者中心的托管关系，集群中已部署的应用和组件仍然可用。如不再需要，请到集群中手动进行清理。',
  '该操作不可撤销，请输入集群名称': '该操作不可撤销，请输入集群名称',
  进行确认: '进行确认',
  '请输入集群名称：{n}': '请输入集群名称：{n}',
  搜索集群名称: '搜索集群名称',
  集群信息: '集群信息',
  集群组件: '集群组件',
  集群特性: '集群特性',
  集群描述: '集群描述',
  集群来源: '集群来源',
  项目: '项目',
  业务: '业务',
  容器日志目录: '容器日志目录',
  '集群访问入口 IP': '集群访问入口 IP',
  'ElasticSearch 集群信息': 'ElasticSearch 集群信息',
  主机: '主机',
  端口: '端口',
  命名空间: '命名空间',
  应用访问类型: '应用访问类型',
  应用域名: '应用域名',
  子路径: '子路径',
  子域名: '子域名',
  组件介绍: '组件介绍',
  组件配置: '组件配置',
  访问方式: '访问方式',
  节点标签: '节点标签',
  组件状态: '组件状态',
  '查看 Values': '查看 Values',
  '使用默认 values 部署即可。': '使用默认 values 部署即可。',
  安装信息: '安装信息',
  '推荐使用的命名空间。如果集群组件是手动安装，请在组件详情中查看实际安装的命名空间。': '推荐使用的命名空间。如果集群组件是手动安装，请在组件详情中查看实际安装的命名空间。',
  不启用: '不启用',
  组件详情: '组件详情',
  '为应用提供负载均等功能。': '为应用提供负载均等功能。',
  '云原生应用的控制引擎，必须安装后才能部署应用。': '云原生应用的控制引擎，必须安装后才能部署应用。',
  'Saas 服务水平扩缩容组件，支持基于资源使用情况调整服务副本数量。': 'Saas 服务水平扩缩容组件，支持基于资源使用情况调整服务副本数量。',
  'Release 名称': 'Release 名称',
  部署信息: '部署信息',
  部署时间: '部署时间',
  部署说明: '部署说明',
  工作负载状态: '工作负载状态',
  '支持提供出口 IP': '支持提供出口 IP',
  允许挂载日志到主机: '允许挂载日志到主机',
  'Ingress 路径是否使用正则表达式': 'Ingress 路径是否使用正则表达式',
  使用蓝鲸日志平台方案采集日志: '使用蓝鲸日志平台方案采集日志',
  使用蓝鲸监控获取资源使用指标: '使用蓝鲸监控获取资源使用指标',
  支持自动扩缩容: '支持自动扩缩容',
  高级设置: '高级设置',
  '节点选择器（nodeSelector）': '节点选择器（nodeSelector）',
  '容忍度（tolerations）': '容忍度（tolerations）',
  '请输入，多个值以英文逗号连接': '请输入，多个值以英文逗号连接',
};
