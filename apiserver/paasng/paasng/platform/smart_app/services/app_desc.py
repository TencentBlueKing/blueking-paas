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
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from paasng.platform.declarative.application.resources import ApplicationDesc
from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.platform.declarative.handlers import get_desc_handler
from paasng.platform.sourcectl.models import SPStat


def get_app_description(stat: SPStat) -> ApplicationDesc:
    """Get application description object from source package stats

    :raises: ValidationError when meta info is invalid or empty
    """
    if not stat.meta_info:
        raise ValidationError(_("找不到任何有效的应用描述信息"))

    try:
        desc = get_desc_handler(stat.meta_info).app_desc
    except DescriptionValidationError as e:
        raise ValidationError(str(e))
    return desc
