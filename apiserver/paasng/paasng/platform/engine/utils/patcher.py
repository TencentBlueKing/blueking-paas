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
from django.utils.functional import cached_property

from paasng.platform.applications.constants import ApplicationType
from paasng.platform.declarative.models import DeploymentDescription
from paasng.platform.engine.constants import RuntimeType
from paasng.platform.engine.exceptions import SkipPatchCode
from paasng.platform.engine.models import Deployment
from paasng.platform.modules.models import Module
from paasng.platform.modules.specs import ModuleSpecs


class SourceCodePatcherWithDBDriver:
    """基于数据库记录驱动的源码 Patcher

    - 目的：基于 CNB 的应用后续启动进程时，必须使用 Procfile 文件，因此自动生成一份
    - 副作用（存疑？）：当普通应用经由 app_desc.yaml 解析并获取应用进程信息失败时，后续仍
    会尝试从 Procfile 文件读取进程信息，变成了一种“托底”逻辑。详情见 ApplicationBuilder
    中调用 get_processes 的部分。
    """

    def __init__(self, module: "Module", source_dir: Path, deployment: Deployment):
        """
        :param module: 模块
        :param source_dir: 源码根路径
        :param deployment :Deployment obj
        """
        self.module = module
        self.source_dir = source_dir
        self.deployment = deployment

    def add_procfile(self):
        """尝试往应用源码目录创建 Procfile 文件, 如果源码已加密, 则注入至应用描述文件目录下"""
        if self.module.application.type == ApplicationType.CLOUD_NATIVE:
            self._add_procfile_for_cnative_app()
        else:
            self._add_procfile_for_default_app()

    def _add_procfile_for_cnative_app(self):
        """「云原生应用」buildpack 构建方式的应用注入 Procfile 文件"""
        if self.module.build_config.build_method == RuntimeType.DOCKERFILE:
            # dockerfile 类型的构建方式不需要注入 procfile
            raise SkipPatchCode("Dockerfile-type builds do not require a Procfile")

        try:
            procfile = self.deploy_description.get_procfile()
        except DeploymentDescription.DoesNotExist:
            raise SkipPatchCode("DeploymentDescription does not exist, skip the injection process")

        if not procfile:
            raise SkipPatchCode("Procfile is undefined")

        # 云原生应用如果 Procfile 已存在则不覆盖
        key = self._make_key("Procfile")
        if key.exists():
            raise SkipPatchCode("Procfile already exists")

        key.parent.mkdir(parents=True, exist_ok=True)
        key.write_text(yaml.safe_dump(procfile))

    def _add_procfile_for_default_app(self):
        """「普通应用」尝试往应用源码目录创建 Procfile 文件"""
        try:
            procfile = self.deploy_description.get_procfile()
        except DeploymentDescription.DoesNotExist:
            raise SkipPatchCode("DeploymentDescription does not exist, skip the injection process")

        if not procfile:
            raise SkipPatchCode("Procfile is undefined")

        # 普通应用如果 Procfile 已存在则不覆盖
        key = self._make_key("Procfile")
        if key.exists():
            raise SkipPatchCode("Procfile already exists")

        key.parent.mkdir(parents=True, exist_ok=True)
        key.write_text(yaml.safe_dump(procfile))

    @cached_property
    def deploy_description(self) -> DeploymentDescription:
        """部署描述文件, 仅普通应用有该模型"""
        return DeploymentDescription.objects.get(deployment=self.deployment)

    @cached_property
    def module_dir(self) -> Path:
        """当前模块代码的路径"""
        user_dir = Path(self.get_user_source_dir())
        if user_dir.is_absolute():
            user_dir = Path(user_dir).relative_to("/")
        return self.source_dir / str(user_dir)

    def get_user_source_dir(self) -> str:
        """Return the directory of the source code which is defined by user."""
        if ModuleSpecs(self.module).deploy_via_package:
            return self.deploy_description.source_dir
        else:
            return self.module.get_source_obj().get_source_dir()

    def _make_key(self, key: str) -> Path:
        # 如果源码目录已加密, 则生成至应用描述文件的目录下.
        if self.module_dir.is_file():
            return self.source_dir / key
        return self.module_dir / key
