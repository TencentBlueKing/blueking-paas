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

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Dict

import yaml
from django.utils.functional import cached_property

from paasng.platform.declarative.handlers import get_deploy_desc_by_module, get_desc_handler
from paasng.platform.engine.utils.source import validate_source_dir_str
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.specs import ModuleSpecs
from paasng.platform.smart_app.services.detector import ManifestDetector
from paasng.platform.smart_app.services.path import LocalFSPath, PathProtocol
from paasng.platform.sourcectl.models import SPStat
from paasng.platform.sourcectl.package.client import BinaryTarClient
from paasng.platform.sourcectl.utils import compress_directory, generate_temp_dir

if TYPE_CHECKING:
    from paasng.platform.modules.models import Module


logger = logging.getLogger(__name__)


class SourceCodePatcher:
    """A helper to patch App SourceCode, base on application description file."""

    @classmethod
    def patch_tarball(cls, module: "Module", tarball_path: Path, working_dir: Path, stat: SPStat) -> Path:
        """Patch S-Mart SourcePackage, then return a newly S-Mart SourcePackage"""
        dest = Path(working_dir) / stat.name
        with generate_temp_dir() as temp_dir:
            BinaryTarClient(tarball_path).export(str(temp_dir.absolute()))
            return cls.patch_source_dir(module=module, root_dir=temp_dir, dest=dest, stat=stat)

    @classmethod
    def patch_source_dir(cls, module: "Module", root_dir: Path, dest: Path, stat: SPStat) -> Path:
        """Patch S-Mart SourcePackage, then return a newly S-Mart SourcePackage"""
        patcher = cls(
            module=module,
            root_dir=LocalFSPath(root_dir),
            desc_data=stat.meta_info,
            relative_path=stat.relative_path,
        )
        # 尝试添加 Procfile
        patcher.add_procfile()
        # 尝试添加 manifest.yaml
        patcher.add_manifest()
        # 重新压缩源码包
        compress_directory(root_dir, dest)
        return dest

    def __init__(self, module: "Module", root_dir: LocalFSPath, desc_data: Dict, relative_path: str = "./"):
        """
        :param module: 模块
        :param root_dir: 源码所在的根目录
        :param desc_data: 应用描述文件中的数据
        :param relative_path: app_description file 的相对源代码的路径(只有在上传 S-Mart 包前的 patch, 才需要传递这个参数.)
        """
        self.module = module
        self.root_dir = root_dir
        self.relative_path = relative_path
        self.desc_data = desc_data
        self.desc_handler = get_desc_handler(desc_data)

        # 当前工作目录
        self._working_dir = self.root_dir / self.relative_path

    @cached_property
    def app_description(self):
        return self.desc_handler.app_desc

    @cached_property
    def deploy_description(self):
        # TODO: 需要保证 module 这个 key 存在
        return get_deploy_desc_by_module(self.desc_data, self.module.name)

    @cached_property
    def source_dir(self) -> LocalFSPath:
        """包含前模块代码的路径。"""
        return LocalFSPath(validate_source_dir_str(self._working_dir.path, self.source_dir_str))

    @cached_property
    def source_dir_str(self) -> str:
        """Return the directory of the source code which is defined by user."""
        # TODO: 让 RepositoryInstance.get_source_dir 屏蔽 source_origin 这个差异
        # 由于 Package 的 source_dir 是由与 VersionInfo 绑定的. 需要调整 API.
        if ModuleSpecs(self.module).deploy_via_package:
            return self.deploy_description.source_dir
        else:
            return self.module.get_source_obj().get_source_dir()

    def _make_key(self, key: str) -> PathProtocol:
        # 如果源码目录已加密, 则生成至应用描述文件的目录下.
        if self.source_dir.is_file():
            return self._working_dir / key
        return self.source_dir / key

    def add_procfile(self):
        """尝试往应用源码目录创建 Procfile 文件, 如果源码已加密, 则注入至应用描述文件目录下"""
        key = self._make_key("Procfile")
        if key.exists():
            logger.warning("Procfile already exists, skip the injection process")
            return
        procfile = self.deploy_description.get_procfile()
        if not procfile:
            logger.warning("Procfile not defined, skip injection process")
            return

        key.write_text(yaml.safe_dump(procfile))

    def add_manifest(self):
        """尝试往源码根目录添加 manifest"""
        if self.module.get_source_origin() != SourceOrigin.S_MART:
            return

        logger.debug("[S-Mart] Try to add manifest to S-Mart tarball.")
        key = self._working_dir / "manifest.yaml"
        if key.exists():
            logger.warning("manifest.yaml already exists, skip.")
            return

        manifest = ManifestDetector(
            package_root=self.root_dir,
            app_description=self.app_description,
            relative_path=self.relative_path,
            source_dir=str(self.source_dir.relative_to(self._working_dir)),
        ).detect()
        key.write_text(yaml.safe_dump(manifest))
