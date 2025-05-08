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

from pydantic import BaseModel, Field

from paasng.utils.structure import prepare_json_field


@prepare_json_field
class SMartAppArtifactMetadata(BaseModel):
    """记录由 smart-app-builder 工具构建出的 Smart 包的元数据

    :param use_cnb: 是否使用 CNB 构建
    :param module_image_tars: 模块使用的镜像 tar, 格式为 {模块名: 镜像 tar 名}
    :param module_proc_entrypoints: 模块进程的 entrypoint, 格式为 {模块名: {进程名: entrypoint}}

    NOTE: smart-app-builder 工具采用了一种应用模块间复用构建包的方式来优化 Smart 包的大小, 具体包括:
    - 镜像共享机制: 采用相同构建方案的模块会共用同一个镜像 tar 文件.
    - 进程 entrypoint 规则: 模块进程的 entrypoint 有单独的生成规则.

    在上传 Smart 包的时候, 通过解析包中 artifact.json 文件, 将各模块与镜像 tar 的对应关系记录到 module_image_tars 中,
    将进程的 entrypoint 信息记录到 module_proc_entrypoints 中.
    """

    use_cnb: bool = False
    module_image_tars: dict[str, str] = Field(default_factory=dict)
    module_proc_entrypoints: dict[str, dict[str, list[str]]] = Field(default_factory=dict)
