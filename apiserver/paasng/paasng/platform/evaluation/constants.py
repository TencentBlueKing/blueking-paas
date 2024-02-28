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
from django.utils.translation import gettext_lazy as _


class EmailReceiverType(str, StructuredEnum):
    """报告邮件接收者类型"""

    PLAT_MANAGER = EnumField("plat_manager", label=_("平台管理员"))
    APP_MANAGER = EnumField("app_manager", label=_("应用管理员"))


class OperationIssueType(str, StructuredEnum):
    """应用运营问题类型"""

    NONE = EnumField("none", label=_("无"))
    OWNERLESS = EnumField("ownerless", label=_("无主"))
    INACTIVE = EnumField("inactive", label=_("不活跃"))
    MISCONFIGURED = EnumField("misconfigured", label=_("配置错误"))
