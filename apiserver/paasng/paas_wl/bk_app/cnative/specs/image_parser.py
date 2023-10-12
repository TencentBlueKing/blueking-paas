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
import logging
from typing import Optional

from django.utils.translation import gettext_lazy as _
from moby_distribution.registry.utils import parse_image

from paas_wl.bk_app.cnative.specs.constants import ApiVersion
from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppResource

logger = logging.getLogger(__name__)


class ImageParser:
    """A Helper for parsing image field in bkapp"""

    def __init__(self, bkapp: BkAppResource):
        self.bkapp = bkapp
        self.image = self.get_image_field(bkapp)

    def get_tag(self) -> Optional[str]:
        """get part `tag` in image field"""
        return parse_image(self.image, default_registry="registry.hub.docker.com").tag

    def get_repository(self) -> str:
        """get part `repository` in image field"""
        parsed = parse_image(self.image, default_registry="registry.hub.docker.com")
        return f"{parsed.domain}/{parsed.name}"

    def get_image_field(self, bkapp: BkAppResource) -> str:
        """get image field from app model resource"""
        image = ""
        if bkapp.apiVersion == ApiVersion.V1ALPHA2:
            if bkapp.spec.build and bkapp.spec.build.image:
                image = bkapp.spec.build.image
            else:
                raise ValueError(_("spec.build.image is missing"))
        elif bkapp.apiVersion == ApiVersion.V1ALPHA1:
            # 兼容 V1ALPHA1
            # 优先使用 web 进程的镜像, 如无 web 进程, 则使用第一个进程的镜像
            images = []
            for proc in bkapp.spec.processes:
                if proc.image:
                    images.append(proc.image)
                    if proc.name == "web":
                        image = proc.image
            if image == "":
                image = images[0] if images else image
            if len(images) > 1:
                logger.warning(
                    "multiple image are defined, "
                    "only the image of the process named web or the first process's image will be used"
                )
        else:
            NotImplementedError("unknown apiVersion: {}".format(bkapp.apiVersion))

        if not image:
            raise ValueError(_("image is missing"))
        return image
