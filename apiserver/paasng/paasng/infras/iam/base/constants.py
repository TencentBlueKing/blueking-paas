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

from blue_krill.data_types.enum import EnumField, StrStructuredEnum


class IAMVersion(StrStructuredEnum):
    """部署环境对接的权限中心版本

    版本的选择是部署环境级别的：V3 与 V4 的授权数据（管理空间、用户组）完全隔离，
    因此不支持在同一环境内按功能模块或按应用混用两个版本。
    """

    V3 = EnumField("v3", label="权限中心 V3")
    V4 = EnumField("v4", label="权限中心 V4")


# V4 列表类接口单页可返回的最大条数，由权限中心侧约定。
# 该值调整时需同步修改，翻页封装依赖它计算请求次数。
V4_LIST_PAGE_SIZE_LIMIT = 100

# V4 批量类接口（批量鉴权、批量授权、批量添加成员等）单次可提交的最大条目数，
# 由权限中心侧约定。超出该值时由批量封装自动分批。
V4_BATCH_OPERATION_LIMIT = 20

# V4 写操作的操作人 header 名称
V4_OPERATOR_HEADER = "X-Bkiam-Operator"
