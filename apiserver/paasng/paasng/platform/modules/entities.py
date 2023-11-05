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
from typing import Dict, List, Optional

from attrs import define

from paasng.platform.engine.constants import RuntimeType
from paasng.platform.modules.models import AppBuildPack, AppSlugBuilder, AppSlugRunner
from paasng.platform.modules.models.build_cfg import ImageTagOptions


@define
class BuildConfig:
    """BuildConfig dataclass, provide similar attribute of modules.models.BuildConfig

    This class is used to keep the response structure of `RegionTemplateViewSet.retrieve`
    similar to `ModuleBuildConfigViewSet.retrieve`
    """

    build_method: RuntimeType
    tag_options: ImageTagOptions

    image: Optional[str] = None
    dockerfile_path: Optional[str] = None
    docker_build_args: Optional[Dict] = None

    buildpacks: Optional[List[AppBuildPack]] = None
    buildpack_builder: Optional[AppSlugBuilder] = None
    buildpack_runner: Optional[AppSlugRunner] = None
