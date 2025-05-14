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
from blue_krill.data_types.enum import EnumField, IntStructuredEnum, StrStructuredEnum
from django.utils.translation import gettext_lazy as _


class ClientRole(IntStructuredEnum):
    """The role of the system API client. Each role has a different set of permissions."""

    NOBODY = EnumField(1, label=_("没有特定角色"))

    BASIC_READER = EnumField(50, label=_("基础可读"))
    BASIC_MAINTAINER = EnumField(60, label=_("基础管理"))
    LIGHT_APP_MAINTAINER = EnumField(70, label=_("轻应用管理"))

    LESSCODE = EnumField(80, label=_("lesscode 系统专用角色"))


class ClientAction(StrStructuredEnum):
    """The action of the system API client, it's referenced by the client role."""

    # 供普通的第三方系统使用
    READ_APPLICATIONS = EnumField("sysapi:read:applications", label=_("读取应用信息"))
    MANAGE_APPLICATIONS = EnumField("sysapi:manage:applications", label=_("管理应用信息"))
    READ_SERVICES = EnumField("sysapi:read:services", label=_("读取增强服务信息"))

    # 仅供平台内部系统使用
    MANAGE_ACCESS_CONTROL = EnumField("sysapi:manage:access_control", label=_("管理应用访问控制"))

    # 供轻应用系统使用
    MANAGE_LIGHT_APPLICATIONS = EnumField("sysapi:manage:light-applications", label=_("管理轻应用"))

    # 仅提供给 LessCode 系统使用
    READ_DB_CREDENTIAL = EnumField("sysapi:read:db-credential", label=_("读取 DB 凭证信息"))
    BIND_DB_SERVICE = EnumField("sysapi:bind:db-service", label=_("绑定 DB 服务"))
