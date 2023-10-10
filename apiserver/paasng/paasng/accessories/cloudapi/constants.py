# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
from blue_krill.data_types.enum import EnumField, StructuredEnum


class ApplyStatusEnum(StructuredEnum):
    PARTIAL_APPROVED = EnumField("partial_approved", label="部分通过")
    APPROVED = EnumField("approved", label="通过")
    REJECTED = EnumField("rejected", label="驳回")
    PENDING = EnumField("pending", label="待审批")


class PermissionStatusEnum(StructuredEnum):
    OWNED = EnumField("owned", label="已拥有")
    REJECTED = EnumField("rejected", label="已拒绝")
    EXPIRED = EnumField("expired", label="已过期")
    PENDING = EnumField("pending", label="申请中")
    NEED_APPLY = EnumField("need_apply", label="未申请")


class PermissionLevelEnum(StructuredEnum):
    UNLIMITED = EnumField("unlimited", label="无限制")
    NORMAL = EnumField("normal", label="普通")
    SENSITIVE = EnumField("sensitive", label="敏感")
    SPECIAL = EnumField("special", label="特殊")


class PermissionActionEnum(StructuredEnum):
    APPLY = EnumField("apply", label="申请")
    RENEW = EnumField("renew", label="续期")


class PermissionApplyExpireDaysEnum(StructuredEnum):
    SIX_MONTH = EnumField(180, label="6个月")
    TWELVE_MONTH = EnumField(360, label="12个月")


class GrantDimensionEnum(StructuredEnum):
    API = EnumField("api", label="按网关")
    RESOURCE = EnumField("resource", label="按资源")
