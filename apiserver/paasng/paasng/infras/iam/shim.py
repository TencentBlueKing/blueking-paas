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

"""按部署环境的配置分发权限中心版本实现

版本由 `BK_IAM_VERSION` 决定，粒度是整个部署环境：V3 与 V4 的授权数据完全隔离，
不支持按功能模块或按应用混用两个版本。非法取值在服务启动时即报错（见 settings）。
"""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from paasng.infras.iam.base.backends import BaseAuthBackend, BaseManagementBackend
from paasng.infras.iam.base.constants import IAMVersion


def get_iam_version() -> IAMVersion:
    """当前部署环境对接的权限中心版本"""
    version = settings.BK_IAM_VERSION
    try:
        return IAMVersion(version)
    except ValueError:
        raise ImproperlyConfigured(f"不支持的 IAM 版本: {version}，可选值为 {[member.value for member in IAMVersion]}")


def get_paas_system_id() -> str:
    """开发者中心在权限中心上注册的系统 ID。V3 与 V4 使用同一套系统 ID"""
    return settings.IAM_PAAS_V3_SYSTEM_ID


def get_plugin_system_id() -> str:
    """插件开发中心在权限中心上注册的系统 ID。V3 与 V4 使用同一套系统 ID"""
    return settings.IAM_PLUGINS_CENTER_SYSTEM_ID


def get_auth_backend() -> BaseAuthBackend:
    """获取当前环境的鉴权实现

    note: 实现按版本延迟导入，避免在只使用某一版本的环境中加载另一版本的依赖
    """
    if get_iam_version() == IAMVersion.V4:
        from paasng.infras.iam.v4.auth import BKIAMV4AuthBackend

        return BKIAMV4AuthBackend()

    from paasng.infras.iam.v3.auth import BKIAMV3AuthBackend

    return BKIAMV3AuthBackend()


def get_system_operator() -> str:
    """无用户上下文（异步任务、管理命令、初始化脚本）时使用的系统操作人

    取值与 V4 客户端缺省操作人一致，为当前应用的 bk_app_code，审计日志中可识别为系统操作。
    """
    return settings.BK_APP_CODE


def get_management_backend(tenant_id: str, operator: str | None = None) -> BaseManagementBackend:
    """获取当前环境的权限管理实现

    :param tenant_id: 租户标识
    :param operator: 操作人。V4 的写操作要求携带该标识，为空时使用 BK_APP_CODE
    """
    if get_iam_version() == IAMVersion.V4:
        from paasng.infras.iam.v4.management import BKIAMV4ManagementBackend

        return BKIAMV4ManagementBackend(tenant_id, operator)

    from paasng.infras.iam.v3.management import BKIAMV3ManagementBackend

    return BKIAMV3ManagementBackend(tenant_id, operator)
