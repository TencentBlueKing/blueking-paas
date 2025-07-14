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

from pathlib import Path

import yaml

from paasng.platform.applications.constants import ApplicationType
from paasng.platform.engine.constants import RuntimeType
from paasng.platform.engine.exceptions import SkipPatchCode
from paasng.platform.engine.models import Deployment
from paasng.platform.modules.models import Module


class SourceCodePatcherWithDBDriver:
    """基于数据库记录驱动的源码 Patcher

    - 目的：基于 CNB 的应用后续启动进程时，必须使用 Procfile 文件，因此自动生成一份
    - 仅当 Procfile 不存在时才会写入文件
    - 副作用（存疑？）：当普通应用经由 app_desc.yaml 解析并获取应用进程信息失败时，后续仍
    会尝试从 Procfile 文件读取进程信息，变成了一种“托底”逻辑。详情见 ApplicationBuilder
    中调用 get_processes 的部分。

    :param module: 模块。
    :param root_dir: 项目源码根目录。
    :param source_dir: 模块所使用的源码（构建）目录，可能和 root_dir 不同。
    :param deployment: Deployment 对象。
    """

    def __init__(self, module: "Module", root_dir: Path, source_dir: Path, deployment: Deployment):
        self.module = module
        self.root_dir = root_dir
        self.source_dir = source_dir
        self.deployment = deployment

        # 如果源码目录已加密（类型为文件而非目录）, 则生成至应用描述文件的目录下
        if self.source_dir.is_file():
            self.procfile_fpath = root_dir / "Procfile"
        else:
            self.procfile_fpath = source_dir / "Procfile"

    def add_procfile(self):
        """尝试往应用源码目录创建 Procfile 文件, 如果源码已加密, 则注入至应用描述文件目录下"""
        # 忽略使用 Dockerfile 构建的云原生应用，无需注入 Procfile
        if (
            self.module.application.type == ApplicationType.CLOUD_NATIVE
            and self.module.build_config.build_method == RuntimeType.DOCKERFILE
        ):
            raise SkipPatchCode("Dockerfile-type builds do not require a Procfile")

        # 适用场景：
        # - 「云原生应用」buildpack 构建方式的应用注入 Procfile 文件
        # - 「普通应用」尝试往应用源码目录创建 Procfile 文件
        procfile = self.deployment.get_procfile()
        if not procfile:
            raise SkipPatchCode("Procfile is undefined")
        if self.procfile_fpath.exists():
            raise SkipPatchCode("Procfile already exists")

        self.procfile_fpath.parent.mkdir(parents=True, exist_ok=True)
        self.procfile_fpath.write_text(yaml.safe_dump(procfile))
