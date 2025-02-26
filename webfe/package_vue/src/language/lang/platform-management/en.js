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
  平台管理: 'Platform Management',
  服务接入: 'Service Integration',
  应用集群: 'App Clusters',
  集群配置: 'Cluster Config',
  集群列表: 'Cluster List',
  未配置: 'Not Configured',
  已配置: 'Configured',
  搜索租户: 'Search Tenant',
  租户: 'Tenant',
  集群: 'Cluster',
  配置: 'Config',
  集群分配: 'Cluster Allocation',
  '集群（预发布环境）': 'Cluster (Staging Env)',
  '集群（生产环境）': 'Cluster (Production Env)',
  '未配置，应用无法部署': 'Not configured, app cannot be deployed',
  前往添加: 'To Add',
  暂无集群可供分配: 'No Clusters Available for Allocation',
  '请先在 [集群列表] 添加集群，方可分配集群。': 'Please add clusters in the [Cluster List] before allocating.',
  分配方式: 'Allocation Method',
  统一分配: 'Unified Allocation',
  按规则分配: 'Rule-based Allocation',
  请选择集群: 'Please Select Cluster',
  '集群分配成功！': 'Cluster Allocation Successful!',
  如果配置了多个集群: 'If multiple clusters are configured',
  '开发者在创建应用时，需要选择集群；如开发者没选择任何值，则使用默认集群。': 'When creating app, developers need to select a cluster; if no selection is made, the default cluster is used.',
  '可选集群({n})': 'Available Clusters ({n})',
  '已选集群({n})': 'Selected Cluster ({n})',
  按环境分配: 'Environment-based Allocation',
  选择全部: 'All',
  暂无已选集群: 'No Selected Clusters',
  添加规则: 'Add Rule',
  '若执行集群扩缩容操作，请及时执行 “同步节点” 操作来更新集群节点状态。': 'If you perform cluster scaling operations, please execute the "Sync Nodes" operation promptly to update the cluster node status.',
  '搜索集群名称、集群ID': 'Search Cluster Name, Cluster ID',
  集群视角: 'Cluster Perspective',
  租户视角: 'Tenant Perspective',
  集群名称: 'Cluster Name',
  可用租户: 'Available Tenants',
  特性: 'Features',
  节点: 'Nodes',
  同步节点: 'Sync Nodes',
  '确认同步节点？': 'Confirm Sync Nodes?',
  '同步集群节点到开发中心，以便应用开启出口 IP 时能绑定到集群所有节点上。': 'Sync cluster nodes to the development center to allow applications to bind to all nodes in the cluster when enabling external IPs.',
  无法删除集群: 'Cannot Delete Cluster',
  '集群（{n}）正在被以下租户、应用使用，无法删除': 'Cluster ({n}) is currently in use by the following tenants and applications and cannot be deleted',
  被: 'Used by',
  等: 'and',
  '个租户使用，请先在集群配置页面，解除租户与集群的分配关系。': 'other tenants. Please first remove the allocation relationship between the tenant and the cluster in the cluster configuration page.',
  'Bound-by': 'Bound by',
  个应用模块绑定: 'app modules',
  '确认删除集群？': 'Confirm delete cluster?',
  '删除集群仅会解除与开发者中心的托管关系，集群中已部署的应用和组件仍然可用。如不再需要，请到集群中手动进行清理。': 'Deleting the cluster will only remove its management relationship with the developer center. Applications and components already deployed in the cluster will still be available. If no longer needed, please manually clean up in the cluster.',
  '该操作不可撤销，请输入集群名称': 'This action is irreversible. Please enter the cluster name',
  进行确认: 'Confirm',
  '请输入集群名称：{n}': 'Please enter the cluster name: {n}',
  搜索集群名称: 'Search Cluster Name',
  集群信息: 'Cluster Info',
  集群组件: 'Cluster Components',
  集群特性: 'Cluster Features',
  集群描述: 'Cluster Description',
  集群来源: 'Cluster Source',
  项目: 'Project',
  业务: 'Business',
  容器日志目录: 'Container Log Directory',
  '集群访问入口 IP': 'Cluster Access Entry IP',
  'ElasticSearch 集群信息': 'ElasticSearch Cluster Info',
  主机: 'Host',
  端口: 'Port',
  命名空间: 'Namespace',
  应用访问类型: 'APP Access Type',
  应用域名: 'App Domain',
  子路径: 'Sub-path',
  子域名: 'Subdomain',
  组件介绍: 'Component Introduction',
  组件配置: 'Component Configuration',
  访问方式: 'Access Method',
  节点标签: 'Node Labels',
  组件状态: 'Component Status',
  '查看 Values': 'View Values',
  '使用默认 values 部署即可。': 'Deploy using default values.',
  安装信息: 'Installation Information',
  '推荐使用的命名空间。如果集群组件是手动安装，请在组件详情中查看实际安装的命名空间。': 'Recommended namespace. If the cluster component is manually installed, please check the actual installed namespace in the component details.',
  不启用: 'Not Enabled',
  组件详情: 'Component Details',
  '为应用提供负载均等功能。': 'Provides load balancing for applications.',
  '云原生应用的控制引擎，必须安装后才能部署应用。': 'Control engine for cloud-native applications, must be installed before deploying applications.',
  'Saas 服务水平扩缩容组件，支持基于资源使用情况调整服务副本数量。': 'SaaS service-level autoscaling component that supports adjusting the services replicas based on resource usage.',
  'Release 名称': 'Release Name',
  部署信息: 'Deploy Info',
  部署时间: 'Deploy Time',
  部署说明: 'Deploy Instructions',
  工作负载状态: 'Workload Status',
  '支持提供出口 IP': 'Supports providing egress IP',
  允许挂载日志到主机: 'Allows mounting logs to host',
  'Ingress 路径是否使用正则表达式': 'Whether Ingress path uses regex',
  使用蓝鲸日志平台方案采集日志: 'Use BK Log Platform for log collection',
  使用蓝鲸监控获取资源使用指标: 'Use BK Monitoring for resource usage metrics',
  支持自动扩缩容: 'Supports auto-scaling',
  高级设置: 'Advanced Settings',
  '节点选择器（nodeSelector）': 'Node Selector (nodeSelector)',
  '容忍度（tolerations）': 'Tolerations (tolerations)',
};
