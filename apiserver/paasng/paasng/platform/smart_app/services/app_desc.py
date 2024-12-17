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

from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy
from rest_framework.exceptions import ValidationError

from paasng.platform.applications.models import Application
from paasng.platform.declarative.application.resources import ApplicationDesc
from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.platform.declarative.handlers import get_desc_handler
from paasng.platform.smart_app.exceptions import GenAppCodeError
from paasng.platform.sourcectl.models import SPStat

logger = logging.getLogger(__name__)


def get_app_description(stat: SPStat) -> ApplicationDesc:
    """Get application description object from source package stats

    :raises: ValidationError when meta info is invalid or empty
    """
    if not stat.meta_info:
        raise ValidationError(gettext_lazy("找不到任何有效的应用描述信息"))

    try:
        desc = get_desc_handler(stat.meta_info).app_desc
    except DescriptionValidationError as e:
        raise ValidationError(str(e))
    return desc


def gen_app_code(raw_code: str) -> str:
    """根据原始应用 code, 生成新的唯一 code

    :param raw_code: 原始 code
    :return: 新的 code, 由"原始 code + 2 位随机字符串"构成
    """
    max_count = 10

    for _ in range(max_count):
        new_app_code = f"{raw_code}-{get_random_string(2).lower()}"
        if not Application.objects.filter(code=new_app_code).exists():
            return new_app_code

    raise GenAppCodeError(f"exceed max count {max_count}")
