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
  当前租户暂无可用集群: '当前租户暂无可用集群',
  您可以: '您可以',
  '1. 联系平台管理员，为当前租户分配可用集群': '1. 联系平台管理员，为当前租户分配可用集群',
  '2. 在 [集群列表] 中添加新集群': '2. 在 [集群列表] 中添加新集群',
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
  租户信息: '租户信息',
  特性: '特性',
  节点: '节点',
  同步节点: '同步节点',
  集群配置未完成: '集群配置未完成',
  '确认同步节点？': '确认同步节点？',
  '同步集群节点到开发者中心，以便应用开启出口 IP 时能绑定到集群所有节点上。': '同步集群节点到开发者中心，以便应用开启出口 IP 时能绑定到集群所有节点上。',
  无法删除集群: '无法删除集群',
  '集群（{n}）正在被以下租户、应用使用，无法删除': '集群（{n}）正在被以下租户、应用使用，无法删除',
  'Bound-by': '被',
  '1. 被 {s} 等 <i>{n}</i> 个租户使用，请先在集群配置页面，解除租户与集群的分配关系。': '1. 被 {s} 等 <i>{n}</i> 个租户使用，请先在集群配置页面，解除租户与集群的分配关系。',
  '被 <i>{n}</i> 个应用模块绑定': '被 <i>{n}</i> 个应用模块绑定',
  '共计 {n} 条': '共计 {n} 条',
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
  集群认证方式: '集群认证方式',
  证书: '证书',
  证书认证机构: '证书认证机构',
  客户端证书: '客户端证书',
  客户端密钥: '客户端密钥',
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
  介绍: '介绍',
  说明: '说明',
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
  '确认删除租户 {k} 的集群分配策略？': '确认删除租户 {k} 的集群分配策略？',
  'Nginx Ingress 控制器，基于 Nginx 实现 HTTP/HTTPS 流量路由、负载均衡、自定义域名、URL 路径规则等功能。': 'Nginx Ingress 控制器，基于 Nginx 实现 HTTP/HTTPS 流量路由、负载均衡、自定义域名、URL 路径规则等功能。',
  '将应用的各类日志采集到 ElasticSearch 集群，以支持后续查询标准输出、预定义的结构化、Nginx 接入层等日志。': '将应用的各类日志采集到 ElasticSearch 集群，以支持后续查询标准输出、预定义的结构化、Nginx 接入层等日志。',
  '云原生应用的关键基建，是开发者中心基于 k8s 能力实现的 operator，承担着云原生应用相关资源的管理，调度等职责。': '云原生应用的关键基建，是开发者中心基于 k8s 能力实现的 operator，承担着云原生应用相关资源的管理，调度等职责。',
  '蓝鲸容器管理平台（BCS）提供的增强型 Pod 水平扩缩容组件，支持按各类指标对应用集成副本数量进行扩缩容。': '蓝鲸容器管理平台（BCS）提供的增强型 Pod 水平扩缩容组件，支持按各类指标对应用集成副本数量进行扩缩容。',
  添加集群: '添加集群',
  编辑集群: '编辑集群',
  基础信息: '基础信息',
  组件安装: '组件安装',
  '为方便接入和管理，请先将集群导入至 BCS': '为方便接入和管理，请先将集群导入至 BCS',
  '如 Master 节点 /root/.kube/config 文件中 admin 用户 user.token 的值': '如 Master 节点 /root/.kube/config 文件中 admin 用户 user.token 的值',
  '用于指引用户配置独立域名的解析，如果集群使用云厂商的 clb 做流量控制，这里需要填写对应的 vip': '用于指引用户配置独立域名的解析，如果集群使用云厂商的 clb 做流量控制，这里需要填写对应的 vip',
  '用于采集应用日志，该配置将在后续安装 bkapp-log-collection 时会生效': '用于采集应用日志，该配置将在后续安装 bkapp-log-collection 时会生效',
  哪些租户在集群分配的时候可以看到这个集群: '哪些租户在集群分配的时候可以看到这个集群',
  'BCS 集群': 'BCS 集群',
  '集群 Server': '集群 Server',
  '集群 Token': '集群 Token',
  'K8S 集群（不推荐，无法使用访问控制台等功能）': 'K8S 集群（不推荐，无法使用访问控制台等功能）',
  子路径: '子路径',
  子域名: '子域名',
  新增域名: '新增域名',
  保存并下一步: '保存并下一步',
  '集群上所有应用共用一个域名，应用的访问地址形如：apps.example.com/appid': '集群上所有应用共用一个域名，应用的访问地址形如：apps.example.com/appid',
  '需要给应用申请一个泛域名（如：*.apps.example.com），应用的访问地址形式如：appid.apps.example.com': '需要给应用申请一个泛域名（如：*.apps.example.com），应用的访问地址形式如：appid.apps.example.com',
  '为方便管理，后续组件都建议安装在这个命名空间下': '为方便管理，后续组件都建议安装在这个命名空间下',
  '如使用自定义的镜像仓库，请确认相关镜像已经推送到该仓库': '如使用自定义的镜像仓库，请确认相关镜像已经推送到该仓库',
  '应用域名需要配置解析到集群的出口 IP': '应用域名需要配置解析到集群的出口 IP',
  '若启用 HTTPS，请在“共享证书”中托管证书，或者在外部网关中配置证书。': '若启用 HTTPS，请在“共享证书”中托管证书，或者在外部网关中配置证书。',
  更新组件配置成功: '更新组件配置成功',
  必要组件: '必要组件',
  组件说明: '组件说明',
  '必须安装这些组件后，集群才能部署蓝鲸应用': '必须安装这些组件后，集群才能部署蓝鲸应用',
  '已经根据前面步骤填写的配置生成 Values。': '已经根据前面步骤填写的配置生成 Values。',
  '使用默认 Values 即可，无需额外配置。': '使用默认 Values 即可，无需额外配置。',
  键: '键',
  值: '值',
  安装: '安装',
  重新安装: '重新安装',
  可选组件: '可选组件',
  运算符: '运算符',
  编辑组件配置: '编辑组件配置',
  '非 BCS 集群需要手动安装集群组件': '非 BCS 集群需要手动安装集群组件',
  '直接使用节点主机网络，nginx 将会将流量转发到节点的 80 & 443 端口。': '直接使用节点主机网络，nginx 将会将流量转发到节点的 80 & 443 端口。',
  '使用 CLB 作为接入层，监听器将流量转发到集群节点的指定的 NodePort。': '使用 CLB 作为接入层，监听器将流量转发到集群节点的指定的 NodePort。',
  '已经根据集群的版本和平台相关设置给集群配置了相关特性。': '已经根据集群的版本和平台相关设置给集群配置了相关特性。',
  '可通过为节点设置污点，并在开发者中心配置容忍度，以将应用部署到指定的集群节点上。': '可通过为节点设置污点，并在开发者中心配置容忍度，以将应用部署到指定的集群节点上。',
  'docker 默认 /var/lib/docker/containers; containerd 默认 /var/lib/containerd.': 'docker 默认 /var/lib/docker/containers; containerd 默认 /var/lib/containerd.',
  最新版本: '最新版本',
  已下发安装任务: '已下发安装任务',
  组件版本更新确认: '组件版本更新确认',
  '不调度（NoSchedule）': '不调度（NoSchedule）',
  '倾向不调度（PreferNoSchedule）': '倾向不调度（PreferNoSchedule）',
  '不执行（NoExecute）': '不执行（NoExecute）',
  'BCS 网关': 'BCS 网关',
  '集群 API 地址类型': '集群 API 地址类型',
  '通过 BCS 提供的网关操作集群，格式如：https://bcs-api.bk.example.com/clusters/BCS-K8S-00000/': '通过 BCS 提供的网关操作集群，格式如：https://bcs-api.bk.example.com/clusters/BCS-K8S-00000/',
  '可通过 IP + Port 或 Service 名称访问，如：https://127.0.0.1:8443，https://kubernetes.default.svc.cluster.local 等': '可通过 IP + Port 或 Service 名称访问，如：https://127.0.0.1:8443，https://kubernetes.default.svc.cluster.local 等',
  集群添加成功: '集群添加成功',
  继续配置: '继续配置',
  支持在集群列表页面继续配置: '支持在集群列表页面继续配置',
  '离开（稍后配置）': '离开（稍后配置）',
  '后续的配置：组件配置、组件安装、集群特性': '后续的配置：组件配置、组件安装、集群特性',
  '可选方案({n})': '可选方案({n})',
  '已选方案({n})': '已选方案({n})',
  服务配置: '服务配置',
  服务方案: '服务方案',
  监控检测: '监控检测',
  配置服务: '配置服务',
  本地增强服务: '本地增强服务',
  远程增强服务: '远程增强服务',
  资源池: '资源池',
  可见: '可见',
  不可见: '不可见',
  '未配置，将影响使用': '未配置，将影响使用',
  '如果配置多个方案：开发者启用增强服务时需要根据 “方案名称” 选择具体的增强服务方案；如开发者未选择任何值，则默认使用已选列表中的第一个方案。': '如果配置多个方案：开发者启用增强服务时需要根据 “方案名称” 选择具体的增强服务方案；如开发者未选择任何值，则默认使用已选列表中的第一个方案。',
  添加方案: '添加方案',
  方案名称: '方案名称',
  所属服务: '所属服务',
  是否可见: '是否可见',
  方案简介: '方案简介',
  方案配置: '方案配置',
  方案详情: '方案详情',
  确认删除方案: '确认删除方案',
  新建方案: '新建方案',
  实例配置: '实例配置',
  已分配: '已分配',
  可回收复用: '可回收复用',
  确认删除服务配置: '确认删除服务配置',
};
