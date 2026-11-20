# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

"""把平台的 e2b 沙箱模板以 CR 形式下发到启用了 e2b 的集群。

数据库是唯一的事实来源：每个模板对应集群里同名的一个 SandboxTemplate 与一个 SandboxPool，
底层 E2B 网关把资源名当作 e2b 的 templateID。各集群的下发结果记在下发状态里，创建沙箱前据此判断模板能否使用。

按层次分为以下模块，上层只依赖下层：

- ``manifests``：资源构造。由模板生成 CR 清单与配置摘要，不读库、不连集群
- ``resources``：资源操作。在单个集群命名空间内增删查平台管理的 CR，不读库、不写下发状态
- ``status``：状态获取。只读下发状态，汇总概览、判断模板在集群上是否可用
- ``states``：状态写入。模板保存、集群下线、同步收尾时维护下发状态
- ``sync``：同步编排。按目标集群下发、清理 CR，并按结果更新下发状态

整体流程与限制见 apiserver/design_notes/e2b-sandbox.md。
"""
