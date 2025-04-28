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

from attrs import define, field


@define
class BuildMetadata:
    """构建元数据

    :param image: 镜像
    :param image_repository: 镜像仓库
    :param use_cnb: 是否使用 cnb 构建
    :param use_dockerfile: 是否使用 Dockerfile 构建
    :param buildpacks: buildpacks 字符串
    :param bkapp_revision_id: 与本次构建关联的 BkApp Revision id
    :param extra_envs: 额外的环境变量
    """

    image: str
    image_repository: str | None = None
    use_dockerfile: bool = False
    use_cnb: bool = False
    buildpacks: str | None = None
    bkapp_revision_id: int | None = None
    extra_envs: dict = field(factory=dict)


@define
class BuildArtifactMetadata:
    """构建制品元数据

    :param use_cnb: 是否使用 cnb 构建
    :param use_dockerfile: 是否使用 Dockerfile 构建
    :param entrypoint: 通用的 entrypoint
    :param proc_entrypoints: 进程的 entrypoint, 格式为 {进程名：entrypoint}.
      如果进程有 entrypoint, 其优先级高于通用的 entrypoint
    """

    use_cnb: bool = field(default=False)
    use_dockerfile: bool = field(default=False)
    entrypoint: list[str] | None = None
    proc_entrypoints: dict[str, list[str]] | None = None
