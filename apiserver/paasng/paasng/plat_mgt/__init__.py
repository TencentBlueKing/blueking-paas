# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
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

"""
Platform Management (plat_mgt)

本模块用于为前端平台管理页面功能提供 API

支持从平台管理员，租户管理员视角对平台相关配置进行管理

包含子模块：
FIXME 子模块划分待定，总体上会对应页面菜单分块设计
- application: 应用相关（如：应用列表，运营评估，部署概览等）
- infras: 基础服务相关（如：应用集群，增强服务，运行时管理，代码库配置等）
- configuration: 配置相关（如：内置环境变量，应用模板等）
- operation: 运营数据（如：应用迁移，部署统计等）
- account: 用户账号管理（如：用户特性管理）
- audit: 操作审计（如：后台管理审计，应用操作审计等）
- third_party: 第三方 API（如：可选租户列表，集群列表等）
"""
