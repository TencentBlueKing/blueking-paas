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
from typing import Optional

from django.utils.translation import gettext_lazy as _
from moby_distribution.registry.utils import parse_image

from paas_wl.cnative.specs.constants import ApiVersion
from paas_wl.cnative.specs.crd.bk_app import BkAppResource


class ImageParser:
    """A Helper for parsing image field in bkapp"""

    def __init__(self, bkapp: BkAppResource):
        if bkapp.apiVersion not in [ApiVersion.V1ALPHA2]:
            raise ValueError(
                _("{value} is not valid, use {required").format(value=bkapp.apiVersion, required=ApiVersion.V1ALPHA2)
            )
        if bkapp.spec.build is None or bkapp.spec.build.image is None:
            raise ValueError(_("spec.build.image is missing"))

        self.bkapp = bkapp
        self.image = bkapp.spec.build.image

    def get_tag(self) -> Optional[str]:
        return parse_image(self.image, default_registry="docker.io").tag

    def get_repository(self) -> str:
        parsed = parse_image(self.image, default_registry="docker.io")
        return f"{parsed.domain}/{parsed.name}"
