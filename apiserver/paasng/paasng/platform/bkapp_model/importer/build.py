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

from moby_distribution.registry.utils import parse_image

from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppBuildConfig
from paasng.platform.modules.models import BuildConfig, Module

logger = logging.getLogger(__name__)


def import_build(module: Module, build: BkAppBuildConfig):
    """Import build data.

    :param build: BKApp `spec.build` object.
    """
    parsed = parse_image(build.image, default_registry="registry.hub.docker.com")
    image_repository = f"{parsed.domain}/{parsed.name}"
    credential_name = build.imageCredentialsName

    cfg = BuildConfig.objects.get_or_create_by_module(module)
    cfg.image_repository = image_repository
    cfg.image_credential_name = credential_name
    cfg.save(update_fields=["image_repository", "image_credential_name", "updated"])
