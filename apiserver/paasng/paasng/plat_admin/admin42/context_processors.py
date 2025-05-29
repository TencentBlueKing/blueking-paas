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

import os

from django.conf import settings

from paasng.core.region.states import RegionType

BKPAAS_BUILD_VERSION = os.getenv("BKPAAS_BUILD_VERSION", "unset")


def admin_config(request):
    return {
        "USER_SELECTOR_LIST_API": getattr(settings, "USER_SELECTOR_LIST_API", "").replace("http://", "//"),
        "BKPAAS_URL": settings.BKPAAS_URL,
        "REGION_CHOICES": dict(RegionType.get_choices()),
        "AUTO_CREATE_REGULAR_USER": settings.AUTO_CREATE_REGULAR_USER,
        "BKPAAS_BUILD_VERSION": BKPAAS_BUILD_VERSION,
    }
