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
from blue_krill.data_types.enum import EnumField, IntStructuredEnum, StrStructuredEnum
from django.utils.translation import gettext_lazy as _


class ClientRole(IntStructuredEnum):
    """The role of the system API client. Each role has a different set of permissions."""

    NOBODY = EnumField(1, label=_("没有特定角色"))

    BASIC_READER = EnumField(50, label=_("基础可读"))
    BASIC_MAINTAINER = EnumField(60, label=_("基础管理"))
    LIGHT_APP_MAINTAINER = EnumField(70, label=_("轻应用管理"))

    LESSCODE = EnumField(80, label=_("lesscode 系统专用角色"))
    AIDEV = EnumField(90, label=_("AIDev 系统专用角色"))
    APP_SPARK = EnumField(100, label=_("AppSpark 系统专用角色"))


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

    # 目前仅供 AIDev 平台使用
    GRANT_APIGW_PERMISSIONS = EnumField("sysapi:grant:apigw-permissions", label=_("授权网关 API 权限"))
    BUILD_SANDBOX_IMAGE = EnumField("sysapi:build:sandbox-image", label=_("构建沙箱镜像"))
    CREATE_AI_AGENT_APP = EnumField("sysapi:create:ai-agent-app", label=_("创建 AI Agent 应用"))

    # AIDev 与 AppSpark 共用：各自只能操作自己管理的应用，归属由视图按调用方角色判断
    UPLOAD_SOURCE_PACKAGE = EnumField("sysapi:upload:source-package", label=_("上传源码包"))
    # 包含部署、查部署结果、中断部署、读取部署日志、下架、查下架结果
    DEPLOY_APPLICATIONS = EnumField("sysapi:deploy:applications", label=_("部署/下架应用"))
    READ_AI_AGENT_APP = EnumField("sysapi:read:ai-agent-app", label=_("查询 AI Agent 应用信息"))

    # 仅供 AppSpark 使用
    CREATE_APP_SPARK_APP = EnumField("sysapi:create:app-spark-app", label=_("创建 AppSpark 应用"))
