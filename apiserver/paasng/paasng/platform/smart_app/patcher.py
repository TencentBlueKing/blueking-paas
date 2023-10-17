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
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from django.utils.functional import cached_property

from paasng.platform.sourcectl.models import SPStat
from paasng.platform.sourcectl.package.client import BinaryTarClient
from paasng.platform.sourcectl.utils import compress_directory, generate_temp_dir
from paasng.platform.declarative.constants import AppDescPluginType
from paasng.platform.declarative.handlers import DescriptionHandler, get_desc_handler
from paasng.platform.smart_app.detector import ManifestDetector
from paasng.platform.smart_app.path import LocalFSPath, PathProtocol
from paasng.platform.applications.constants import AppLanguage
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.specs import ModuleSpecs

if TYPE_CHECKING:
    from paasng.platform.modules.models import Module


logger = logging.getLogger(__name__)


class SourceCodePatcher:
    """A helper to patch App SourceCode, base on application description file."""

    @classmethod
    def patch_tarball(cls, module: 'Module', tarball_path: Path, working_dir: Path, stat: SPStat) -> Path:
        """Patch S-Mart SourcePackage, then return a newly S-Mart SourcePackage"""
        dest = Path(working_dir) / stat.name
        with generate_temp_dir() as temp_dir:
            BinaryTarClient(tarball_path).export(str(temp_dir.absolute()))
            return cls.patch_source_dir(module=module, source_dir=temp_dir, dest=dest, stat=stat)

    @classmethod
    def patch_source_dir(cls, module: 'Module', source_dir: Path, dest: Path, stat: SPStat) -> Path:
        """Patch S-Mart SourcePackage, then return a newly S-Mart SourcePackage"""
        patcher = cls(
            module=module,
            source_dir=LocalFSPath(source_dir),
            desc_handler=get_desc_handler(stat.meta_info),
            relative_path=stat.relative_path,
        )
        # 尝试添加 Procfile
        patcher.add_procfile()
        # 尝试添加 requirements.txt
        patcher.add_requirements_txt()
        # 尝试添加 manifest.yaml
        patcher.add_manifest()
        # 重新压缩源码包
        compress_directory(source_dir, dest)
        return dest

    def __init__(
        self, module: 'Module', source_dir: PathProtocol, desc_handler: DescriptionHandler, relative_path: str = "./"
    ):
        """
        :param module: 模块
        :param source_dir: 源码根路径
        :param desc_handler :应用描述文件处理器
        :param relative_path: app_description file 的相对源代码的路径(只有在上传 S-Mart 包前的 patch, 才需要传递这个参数.)
        """
        self.module = module
        self.source_dir = source_dir
        self.relative_path = relative_path
        self.desc_handler = desc_handler

    @cached_property
    def app_description(self):
        return self.desc_handler.app_desc

    @cached_property
    def deploy_description(self):
        # TODO: 需要保证 module 这个 key 存在
        return self.desc_handler.get_deploy_desc(self.module.name)

    @cached_property
    def module_dir(self) -> PathProtocol:
        """当前模块代码的路径"""
        user_dir = Path(self.get_user_source_dir())
        if user_dir.is_absolute():
            user_dir = Path(user_dir).relative_to('/')
        return self.source_dir / self.relative_path / str(user_dir)

    def get_user_source_dir(self) -> str:
        """Return the directory of the source code which is defined by user."""
        # TODO: 让 RepositoryInstance.get_source_dir 屏蔽 source_origin 这个差异
        # 由于 Package 的 source_dir 是由与 VersionInfo 绑定的. 需要调整 API.
        if ModuleSpecs(self.module).deploy_via_package:
            return self.deploy_description.source_dir
        else:
            return self.module.get_source_obj().get_source_dir()

    def _make_key(self, key: str) -> PathProtocol:
        # 如果源码目录已加密, 则生成至应用描述文件的目录下.
        if self.module_dir.is_file():
            return self.source_dir / self.relative_path / key
        return self.module_dir / key

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

    def add_requirements_txt(self):
        """尝试往 Python 类型的应用源码目录创建 requirements.txt 文件, 如果源码已加密, 则注入至应用描述文件目录下"""
        key = self._make_key("requirements.txt")
        plugin = self.app_description.get_plugin(AppDescPluginType.APP_LIBRARIES)
        libraries = (plugin or {}).get("data", [])

        if self.deploy_description.language != AppLanguage.PYTHON:
            logger.debug("Only handle python app.")
            return

        if not libraries:
            logger.warning("Undefined libraries, skip add `requirements.txt`.")
            return

        if key.exists():
            logger.warning(f"file<{key}> in package will be overwrite!.")

        key.write_text("\n".join([f"{lib['name']}=={lib['version']}" for lib in libraries]))

    def add_manifest(self):
        """尝试往源码根目录添加 manifest"""
        if self.module.get_source_origin() != SourceOrigin.S_MART:
            return

        logger.debug("[S-Mart] Try to add manifest to S-Mart tarball.")
        key = self.source_dir / self.relative_path / "manifest.yaml"
        if key.exists():
            logger.warning("manifest.yaml already exists, skip.")
            return

        manifest = ManifestDetector(
            package_root=self.source_dir,
            app_description=self.app_description,
            relative_path=self.relative_path,
            source_dir=str(self.module_dir.relative_to(self.source_dir / self.relative_path)),
        ).detect()
        key.write_text(yaml.safe_dump(manifest))
