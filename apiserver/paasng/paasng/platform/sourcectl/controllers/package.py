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
import shutil
from os import PathLike
from pathlib import Path
from typing import List, Optional, Tuple

from paasng.platform.modules.models.module import Module
from paasng.platform.sourcectl.constants import VersionType
from paasng.platform.sourcectl.models import AlternativeVersion, SourcePackage, VersionInfo
from paasng.platform.sourcectl.package.client import BasePackageClient, get_client

logger = logging.getLogger(__name__)


class PackageController:
    """This class provides the basic method for reading source packages"""

    def __init__(self, module: "Module"):
        self.module = module
        self._client: Optional[BasePackageClient] = None

    @classmethod
    def init_by_module(cls, module: "Module", operator: Optional[str] = None):
        return cls(module)

    def get_client(self, **kwargs) -> BasePackageClient:
        """[private] 根据源码包存储信息, 获取对应的源码包操作客户端"""
        return get_client(package=kwargs["package"])

    def extract_version_info(self, version_info: VersionInfo) -> Tuple[str, str]:
        """[private] 将 version_info 转换成 version_name 和 revision"""
        return version_info.version_name, version_info.revision

    def touch(self) -> bool:
        """Package 总是能访问远程仓库"""
        return True

    def export(self, local_path: "PathLike", version_info: VersionInfo):
        """解压缩指定版本(version_info)的源码包的内容的指定的位置(local_path)"""
        logger.debug("[sourcectl] export files to %s, version<%s>", local_path, version_info)
        _, version = self.extract_version_info(version_info)
        package_storage = self.module.packages.get(version=version)
        cli = self.get_client(package=package_storage)
        try:
            cli.export(str(local_path))
        finally:
            cli.close()

        if not package_storage.relative_path:
            return

        # The source file may have a relative path (e.g. app_code/app_desc.yaml and so on.),
        # So we need to move the files in that directory into local_path
        local_path_obj = Path(local_path)
        source_path = local_path_obj / package_storage.relative_path

        if local_path_obj == source_path:
            return

        abs_source_path = source_path.absolute()
        for child in abs_source_path.iterdir():
            # Move all child contents into local_path
            shutil.move(str(child), str(local_path_obj))
        shutil.rmtree(str(abs_source_path))

    def list_alternative_versions(self) -> List[AlternativeVersion]:
        """仓库级: 罗列所有可用的版本"""
        qs = SourcePackage.default_objects.filter(module_id=self.module.pk).order_by("created")
        items = [
            AlternativeVersion(
                name=info.version,
                type=VersionType.PACKAGE.value if info.storage_engine != "docker" else VersionType.TAG.value,
                revision=info.version,
                url=info.storage_url,
                last_update=info.updated,
                extra=dict(
                    package_size=info.package_size,
                    is_deleted=info.is_deleted,
                ),
            )
            for info in qs
        ]
        return items

    def inspect_version(self, version_info: VersionInfo) -> AlternativeVersion:
        """查询指定版本的具体信息"""
        _, version = self.extract_version_info(version_info)
        info = self.module.packages.get(version=version)
        return AlternativeVersion(
            name=info.version,
            type=VersionType.PACKAGE.value if info.storage_engine != "docker" else VersionType.TAG.value,
            revision=info.version,
            url=info.storage_url,
            last_update=info.updated,
            extra=dict(
                package_size=info.package_size,
                is_deleted=info.is_deleted,
            ),
        )

    def extract_smart_revision(self, smart_revision: str) -> str:
        if ":" not in smart_revision:
            return smart_revision

        _, package_name = smart_revision.split(":", 1)
        # NOTE: 为了兼容 svn/git 的交互协议, 允许通过传递 package_name 来部署最后一个以 package_name 命名的版本。
        if obj_by_pkg_name := self.module.packages.filter(package_name=package_name).last():
            return obj_by_pkg_name.version
        # NOTE: 与 LessCode 那边约定, 通过 url 上传包时会用 version 来取代 package_name, 因此这里做一个兼容。
        elif obj_by_version := self.module.packages.filter(version=package_name).last():
            return obj_by_version.version

        raise SourcePackage.DoesNotExist

    def build_url(self, version_info: VersionInfo) -> str:
        _, version = self.extract_version_info(version_info)
        package_storage = self.module.packages.get(version=version)
        return package_storage.storage_url
