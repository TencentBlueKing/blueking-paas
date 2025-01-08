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
import logging

from djagno.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from paasng.core.tenant.constants import AppTenantMode
from paasng.core.tenant.user import DEFAULT_TENANT_ID, Tenant, get_tenant
from paasng.infras.accounts.models import User
from paasng.platform.applications.models import Application

logger = logging.getLogger(__name__)


def validate_app_tenant_params(user: User, raw_app_tenant_mode: str | None) -> tuple[AppTenantMode, str, Tenant]:
    """Validate the params related with multi-tenant feature.

    :param user: The user who is creating the application.
    :param raw_app_tenant_mode: The app tenant mode in params.
    :returns: A tuple, the items: (app_tenant_mode, app_tenant_id, tenant).
    """
    tenant = get_tenant(user)
    app_tenant_mode: AppTenantMode
    if tenant.is_stub:
        app_tenant_mode = AppTenantMode.GLOBAL
    else:
        # The default tenant mode is SINGLE when multi-tenant mode is enabled
        app_tenant_mode = AppTenantMode.SINGLE if not raw_app_tenant_mode else AppTenantMode(raw_app_tenant_mode)
        if app_tenant_mode == AppTenantMode.GLOBAL and not tenant.is_op_type:
            raise ValidationError(_("当前不允许创建全租户可用的应用"))

    app_tenant_id = "" if app_tenant_mode == AppTenantMode.GLOBAL else tenant.id
    return app_tenant_mode, app_tenant_id, tenant


def get_tenant_id_for_app(app_code: str) -> str:
    # 若果未开启多租户，直接返回默认租户，减少一次 DB 查询操作
    if not settings.ENABLE_MULTI_TENANT_MODE:
        return DEFAULT_TENANT_ID

    try:
        app = Application.objects.get(code=app_code)
    except Application.DoesNotExist:
        logger.warning("Application: %s DoesNotExist", app_code)
        return ""
    return app.tenant_id
