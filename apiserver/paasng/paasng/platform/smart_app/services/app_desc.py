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
from typing import TYPE_CHECKING

from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from paasng.platform.applications.models import Application
from paasng.platform.declarative.application.resources import ApplicationDesc
from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.platform.declarative.handlers import get_desc_handler
from paasng.platform.smart_app.exceptions import GenAppCodeError
from paasng.platform.sourcectl.models import SPStat

if TYPE_CHECKING:
    from paasng.core.tenant.utils import AppTenantInfo

logger = logging.getLogger(__name__)


def get_app_description(stat: SPStat, app_tenant_info: "AppTenantInfo") -> ApplicationDesc:
    """Get application description object from source package stats

    NOTE: 该函数会将 app_tenant_info 注入到 stat.meta_info["tenant"] 中，调用方后续可直接
    使用 stat.meta_info（如传给 get_desc_handler）而无需再次注入。

    :param stat: Source package stats, its meta_info 会被修改以包含 tenant 信息。
    :param app_tenant_info: 待注入的租户信息。
    :raises: ValidationError when meta info is invalid or empty
    """
    if not stat.meta_info:
        raise ValidationError(_("找不到任何有效的应用描述信息"))

    stat.meta_info["tenant"] = {
        "app_tenant_mode": app_tenant_info.app_tenant_mode,
        "app_tenant_id": app_tenant_info.app_tenant_id,
        "tenant_id": app_tenant_info.tenant_id,
    }

    try:
        desc = get_desc_handler(stat.meta_info).app_desc
    except DescriptionValidationError as e:
        raise ValidationError(str(e))
    return desc


def gen_app_code_when_conflict(original_code: str) -> str:
    """当原始应用 code 已存在时(与存量应用冲突)，生成新的 code

    NOTE: 多租户模式下，同一个 Smart 包可以创建多个 Smart 应用, 但是 code 需要保持唯一.
    该函数可用于创建 Smart 应用时, 生成推荐的新 code, 解决 code 冲突的问题

    :param original_code: 原始 code
    :return: 新的 code, 由"原始 code + 2 位随机字符串"构成
    """
    max_count = 10

    for __ in range(max_count):
        new_app_code = f"{original_code}-{get_random_string(2).lower()}"
        if not Application.objects.filter(code=new_app_code).exists():
            return new_app_code

    raise GenAppCodeError(f"exceed max count {max_count}")
