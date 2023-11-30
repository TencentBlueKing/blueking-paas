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
from typing import TYPE_CHECKING, List, Optional

from typing_extensions import Protocol

from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.sourcectl.controllers.docker import DockerRegistryController
from paasng.platform.sourcectl.models import AlternativeVersion, VersionInfo
from paasng.platform.sourcectl.repo_controller import RepoController, get_repo_controller

if TYPE_CHECKING:
    from paasng.platform.modules.models.module import Module


class DeployableVersionService(Protocol):
    """DeployableVersionService 负责管理当前模块的可部署的版本信息:
    - 列举当前所有可选的有名字的版本号，通常包括 branch, tag 等
    - 拼接生成指定版本的项目源码的可访问地址
    - 将有名字的版本号（Named Version）转换成更具体的版本号, 例如，将 Git 的 master 分支转换成 SHA Commit ID
    """

    def touch(self) -> bool:
        """尝试访问远程仓库, 试探是否有访问权限

        :return: 是否有权限
        """

    def build_url(self, version_info: VersionInfo) -> str:
        """拼接生成指定版本的项目源码的可访问地址

        :param version_info: 指定版本信息
        """

    def extract_smart_revision(self, smart_revision: str) -> str:
        """将有名字的版本号（Named Version）转换成更具体的版本号, 例如，将 Git 的 master 分支转换成 SHA Commit ID

        :param smart_revision: 有名字的版本号，比如 master
        """

    def list_alternative_versions(self) -> List[AlternativeVersion]:
        """列举当前所有可选的有名字的版本号，通常包括 branch, tag 等"""

    def inspect_version(self, version_info: VersionInfo) -> AlternativeVersion:
        """查询指定版本的具体信息"""


class RepoVersionService:
    def __init__(self, repo_controller: RepoController):
        self.repo_controller = repo_controller

    def touch(self) -> bool:
        """尝试访问远程仓库, 试探是否有访问权限

        :return: 是否有权限
        :raise Exception: the reason why permission deny
        """
        return self.repo_controller.touch()

    def build_url(self, version_info: VersionInfo) -> str:
        """拼接生成指定版本的项目源码的可访问地址

        :param version_info: 指定版本信息
        """
        return self.repo_controller.build_url(version_info)

    def extract_smart_revision(self, smart_revision: str) -> str:
        """将有名字的版本号（Named Version）转换成更具体的版本号, 例如，将 Git 的 master 分支转换成 SHA Commit ID

        :param smart_revision: 有名字的版本号，比如 master
        """
        return self.repo_controller.extract_smart_revision(smart_revision)

    def list_alternative_versions(self) -> List[AlternativeVersion]:
        """列举当前所有可选的有名字的版本号，通常包括 branch, tag 等"""
        return self.repo_controller.list_alternative_versions()

    def inspect_version(self, version_info: VersionInfo) -> AlternativeVersion:
        """查询指定版本的具体信息"""
        raise NotImplementedError


def get_version_service(module: "Module", operator: Optional[str] = None) -> DeployableVersionService:
    source_origin = module.get_source_origin()

    if source_origin in [SourceOrigin.AUTHORIZED_VCS, SourceOrigin.SCENE]:
        return RepoVersionService(get_repo_controller(module, operator))
    elif source_origin == SourceOrigin.IMAGE_REGISTRY:
        return DockerRegistryController.init_by_module(module, operator)
    elif source_origin in [SourceOrigin.BK_LESS_CODE, SourceOrigin.S_MART]:
        from paasng.platform.sourcectl.controllers.package import PackageController

        return PackageController.init_by_module(module, operator)
    else:
        raise NotImplementedError
