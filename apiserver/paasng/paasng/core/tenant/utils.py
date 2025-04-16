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
from attrs import define
from django.conf import settings

from paasng.core.tenant.constants import AppTenantMode
from paasng.core.tenant.user import DEFAULT_TENANT_ID, OP_TYPE_TENANT_ID


@define
class AppTenantInfo:
    """应用租户相关的配置，字段间关系的详细说明如下:

    1. app_tenant_mode 和 app_tenant_id 字段共同控制了应用的“可用范围”，可能的组合包括：
    - app_tenant_mode: "global", app_tenant_id: ""，表示应用在全租户范围内可用。
    - app_tenant_mode: "single", app_tenant_id: "foo"，表示应用仅在 foo 租户范围内可用。
    应用的“可用范围”将影响对应租户的用户是否可在桌面上看到此应用，以及是否能通过应用链接访问
    应用（不在“可用范围”内的用户请求将被拦截）。

    2. app_tenant_id 和 tenant_id 字段的区别

    虽然这两个字段都存储“租户”，且值可能相同，但二者有本质区别。tenant_id 是系统级字段，值
    总是等于当前这条数据的所属租户，它确定了数据的所有权。而 app_tenant_id 是业务功能层面的
    字段，它和 app_tenant_mode 共同控制前面提到的业务功能——应用“可用范围”。

    :param app_tenant_mode: 应用在租户层面的可用范围，可选值：全租户、指定租户
    :param app_tenant_id: 应用租户 ID
    :param tenant_id: 应用所属租户
    """

    app_tenant_mode: AppTenantMode
    app_tenant_id: str
    tenant_id: str


def validate_app_tenant_info(raw_app_tenant_mode: str, raw_app_tenant_id: str) -> AppTenantInfo:
    """验证租户信息，并根据 app_tenant_mode、app_tenant_id 获取应用所属租户 ID

    NOTE：通过系统 API、命令行等创建应用时，无法从 request 请求中获取租户信息，需要通过参数传递。
    其中，所属租户 tenant_id 是开发者中心自身的逻辑，为减少用户理解成本可以根据其他 2 个参数确定。

    :param raw_app_tenant_mode: 租户类型
    :param raw_app_tenant_id: 租户 ID, 如果是全租户应用，则为空

    :raise ValueError: raw_app_tenant_mode 和 raw_app_tenant_mode 不匹配时抛出异常
    """
    # 非多租户模式下，应用的租户信息是固定的
    # NOTE：系统 API，命令行等创建应用为了向前兼容，默认的参数为全租户应用。所以未开启多租户时不校验参数。
    if not settings.ENABLE_MULTI_TENANT_MODE:
        return AppTenantInfo(
            app_tenant_mode=AppTenantMode.SINGLE,
            app_tenant_id=DEFAULT_TENANT_ID,
            tenant_id=DEFAULT_TENANT_ID,
        )

    if raw_app_tenant_mode == AppTenantMode.GLOBAL:
        # 全租户应用的 app_tenant_id 为空
        if raw_app_tenant_id:
            raise ValueError("For a global-tenant app, the app_tenant_id must be empty.")

        # 仅运营租户能创建全租户应用
        return AppTenantInfo(
            app_tenant_mode=AppTenantMode.GLOBAL,
            app_tenant_id="",
            tenant_id=OP_TYPE_TENANT_ID,
        )

    # 单租户应用，必须指定 app_tenant_id
    if not raw_app_tenant_id:
        raise ValueError("For a single-tenant app, the app_tenant_id must be specified.")

    return AppTenantInfo(
        app_tenant_mode=AppTenantMode.SINGLE,
        app_tenant_id=raw_app_tenant_id,
        tenant_id=raw_app_tenant_id,
    )
