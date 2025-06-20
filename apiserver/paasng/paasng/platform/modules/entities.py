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

from typing import Dict, List, Optional

from attrs import define, field

from paasng.platform.engine.constants import RuntimeType
from paasng.platform.modules.models import AppBuildPack, AppSlugBuilder, AppSlugRunner
from paasng.platform.modules.models.build_cfg import ImageTagOptions


@define
class BuildConfig:
    """BuildConfig dataclass, provide similar attribute of modules.models.BuildConfig

    This class is used to keep the response structure of `TemplateDetailedViewSet.retrieve`
    similar to `ModuleBuildConfigViewSet.retrieve`
    """

    build_method: RuntimeType
    tag_options: ImageTagOptions

    image_repository: Optional[str] = None
    image_credential: Optional[Dict] = None

    dockerfile_path: Optional[str] = None
    docker_build_args: Optional[Dict] = None

    buildpacks: Optional[List[AppBuildPack]] = None
    buildpack_builder: Optional[AppSlugBuilder] = None
    buildpack_runner: Optional[AppSlugRunner] = None


@define(frozen=True)
class VcsInitResult:
    """代码初始化结果

    :param code: 状态码，"OK" 表示成功，其他表示错误码
    :param extra_info: 额外信息，包含下载地址等
    :param dest_type: 目标存储类型（如: s3/bkrepo)
    :param error: 错误信息，成功时为空字符串
    """

    code: str
    extra_info: dict = field(factory=dict)
    dest_type: str = "null"
    error: str = ""

    def is_success(self) -> bool:
        return self.code == "OK"


@define
class ModuleInitResult:
    """模块初始化结果数据类"""

    source_init_result: VcsInitResult = field(factory=lambda: VcsInitResult(code="OK"))
