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


class CollectionTaskStatus(str, StructuredEnum):
    """采集任务状态"""

    RUNNING = EnumField("running", label=_("运行中"))
    FINISHED = EnumField("finished", label=_("已完成"))


class EmailReceiverType(str, StructuredEnum):
    """邮件接收者类型"""

    PLAT_ADMIN = EnumField("plat_admin", label=_("平台管理员"))
    APP_ADMIN = EnumField("app_admin", label=_("应用管理员"))


class OperationIssueType(str, StructuredEnum):
    """应用运营问题类型"""

    NONE = EnumField("none", label=_("无"))
    OWNERLESS = EnumField("ownerless", label=_("无主"))
    IDLE = EnumField("idle", label=_("闲置"))
    UNVISITED = EnumField("unvisited", label=_("无用户访问"))
    MAINTAINLESS = EnumField("maintainless", label=_("缺少维护"))
    UNDEPLOY = EnumField("undeploy", label=_("未部署/已下线"))
    MISCONFIGURED = EnumField("misconfigured", label=_("配置不当"))
