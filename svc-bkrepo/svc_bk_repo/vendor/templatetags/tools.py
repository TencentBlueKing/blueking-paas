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
from django import template
from svc_bk_repo.vendor.render import humanize_bytes

register = template.Library()


@register.filter(name="humanize_bytes")
def _humanize_bytes(bytevalue: int, default: str = None):
    try:
        return humanize_bytes(bytevalue)
    except Exception:
        if default:
            return default
        raise


@register.filter(name="humanize_percent")
def _humanize_percent(percent: float):
    if not percent:
        # 不限制使用率或者使用率0
        return "0"
    elif percent < 1e-2:
        return "<0.01"
    else:
        return round(percent, 2)
