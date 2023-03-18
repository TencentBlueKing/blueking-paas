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
from dataclasses import dataclass
from typing import Optional

from paasng.dev_resources.sourcectl.models import RepoBasicAuthHolder
from paasng.extensions.smart_app.conf import bksmart_settings
from paasng.extensions.smart_app.utils import SMartImageManager
from paasng.platform.modules.models.module import Module
from paasng.platform.modules.specs import ModuleSpecs


@dataclass
class ImageCredential:
    registry: str
    username: str
    password: str


class ImageCredentialManager:
    """A Helper provide the image pull secret for the given Module"""

    def __init__(self, module: Module):
        self.module = module

    def provide(self) -> Optional[ImageCredential]:
        if ModuleSpecs(self.module).deploy_via_package:
            named = SMartImageManager(self.module).get_image_info()
            return ImageCredential(
                registry=f"{named.domain}/{named.name}",
                username=bksmart_settings.registry.username,
                password=bksmart_settings.registry.password,
            )
        source_obj = self.module.get_source_obj()
        repo_full_url = source_obj.get_repo_url()
        try:
            holder = RepoBasicAuthHolder.objects.get_by_repo(module=self.module, repo_obj=source_obj)
            username, password = holder.basic_auth
        except RepoBasicAuthHolder.DoesNotExist:
            username = password = None

        if repo_full_url and username and password:
            return ImageCredential(registry=repo_full_url, username=username, password=password)
        return None
