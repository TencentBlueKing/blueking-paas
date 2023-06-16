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
"""Manage configurations related with source files"""
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Optional, Tuple

import yaml
from typing_extensions import Protocol

from paasng.dev_resources.sourcectl import exceptions
from paasng.dev_resources.sourcectl.models import VersionInfo
from paasng.dev_resources.sourcectl.package.client import BasePackageClient, get_client
from paasng.dev_resources.sourcectl.repo_controller import RepoController, get_repo_controller
from paasng.platform.modules.constants import SourceOrigin

if TYPE_CHECKING:
    from paasng.platform.modules.models.module import Module


logger = logging.getLogger(__name__)


_current_path = Path(".")


class MetaDataReader(Protocol):
    """Protocol to read metadata for deploy"""

    def get_procfile(self, version_info: VersionInfo) -> Dict[str, str]:
        """Read Procfile config from repository

        :raises: exceptions.GetProcfileError
        """

    def get_app_desc(self, version_info: VersionInfo) -> Dict:
        """Read app.yaml/app_desc.yaml from repository

        :raises: exceptions.GetAppYamlError
        """

    def get_dockerignore(self, version_info: VersionInfo) -> str:
        """Read .dockerignore from repository

        :raises: exceptions.GetDockerIgnoreError
        """


class MetaDataFileReader:
    source_dir: Path = Path(".")
    error_tips: str = ""

    def read_file(self, file_path: str, version_info: VersionInfo) -> bytes:
        """从当前仓库指定版本(version_info)的代码中读取指定文件(file_path) 的内容"""
        raise NotImplementedError

    def get_procfile(self, version_info: VersionInfo) -> Dict[str, str]:
        """Read Procfile config from repository

        :raises: exceptions.GetProcfileError
        """
        possible_keys = ['Procfile']
        if self.source_dir != Path("."):
            possible_keys = [str(self.source_dir / 'Procfile'), 'Procfile']

        content = None
        for possible_key in possible_keys:
            try:
                content = self.read_file(possible_key, version_info)
                break
            except Exception:
                continue
        if content is None:
            error_msg = 'Can not read Procfile file from repository'
            if self.error_tips:
                error_msg += f', {self.error_tips}'
            raise exceptions.GetProcfileError(error_msg)

        try:
            procfile = yaml.load(content)
        except Exception as e:
            raise exceptions.GetProcfileError('file "Procfile"\'s format is not YAML') from e

        if not isinstance(procfile, dict):
            raise exceptions.GetProcfileError('file "Procfile" must be dict type')
        return procfile

    def get_app_desc(self, version_info: VersionInfo) -> Dict:
        """Read app.yaml/app_desc.yaml from repository

        :raises: exceptions.GetAppYamlError
        """
        possible_keys = ["app_desc.yaml", "app_desc.yml", "app.yml", "app.yaml"]
        if self.source_dir != Path("."):
            # Note: 为了保证不影响源码包部署的应用, 优先从根目录读取 app_desc.yaml, 随后再尝试从 source_dir 目录读取
            possible_keys = [
                "app_desc.yaml",
                "app_desc.yml",
                str(self.source_dir / "app_desc.yaml"),
                str(self.source_dir / "app_desc.yml"),
                "app.yml",
                "app.yaml",
                str(self.source_dir / "app.yml"),
                str(self.source_dir / "app.yaml"),
            ]

        content = None
        for possible_key in possible_keys:
            try:
                content = self.read_file(possible_key, version_info)
                break
            except exceptions.DoesNotExistsOnServer:
                continue
        if content is None:
            error_msg = 'Can not read app description file from repository'
            if self.error_tips:
                error_msg += f', {self.error_tips}'
            raise exceptions.GetAppYamlError(error_msg)

        try:
            app_description = yaml.load(content)
        except Exception as e:
            raise exceptions.GetAppYamlError('file "app.yaml"\'s format is not YAML') from e
        if not isinstance(app_description, dict):
            raise exceptions.GetAppYamlError('file "app.yaml" must be dict type')
        return app_description

    def get_dockerignore(self, version_info: VersionInfo) -> str:
        """Read .dockerignore config from repository

        :raises: exceptions.GetDockerIgnoreError
        """
        possible_keys = ['.dockerignore']
        if self.source_dir != Path("."):
            possible_keys = [str(self.source_dir / '.dockerignore'), '.dockerignore']

        content = None
        for possible_key in possible_keys:
            try:
                content = self.read_file(possible_key, version_info)
                break
            except Exception:
                continue
        if content is None:
            error_msg = 'Can not read .dockerignore file from repository'
            if self.error_tips:
                error_msg += f', {self.error_tips}'
            raise exceptions.GetDockerIgnoreError(error_msg)
        return content.decode()


class VCSMetaDataReader(MetaDataFileReader):
    error_tips = "please ensure the file exists in the repository and the network or proxy is working normally"

    def __init__(self, repo_controller: RepoController, source_dir: Path = _current_path):
        self.repo_controller = repo_controller
        self.source_dir = source_dir

    def read_file(self, file_path: str, version_info: VersionInfo) -> bytes:
        """从当前仓库指定版本(version_info)的代码中读取指定文件(file_path) 的内容"""
        return self.repo_controller.read_file(file_path, version_info)


class PackageMetaDataReader(MetaDataFileReader):
    error_tips = "please ensure the file exists in the package"

    def __init__(self, module: 'Module', source_dir: Path = _current_path):
        self.module = module
        self._client: Optional[BasePackageClient] = None
        self.source_dir = source_dir

    def get_client(self, **kwargs) -> BasePackageClient:
        """[private] 根据源码包存储信息, 获取对应的源码包操作客户端"""
        return get_client(package=kwargs["package"])

    def extract_version_info(self, version_info: VersionInfo) -> Tuple[str, str]:
        """[private] 将 version_info 转换成 version_name 和 revision"""
        return version_info.version_name, version_info.revision

    def read_file(self, file_path: str, version_info: VersionInfo) -> bytes:
        """从指定版本(version_info)的源码包读取指定位置(file_path)的文件的内容"""
        logger.debug("[sourcectl] reading file from %s, version<%s>", file_path, version_info)
        _, version = self.extract_version_info(version_info)
        package_storage = self.module.packages.get(version=version)
        cli = self.get_client(package=package_storage)
        try:
            return cli.read_file(str(self.source_dir / file_path))
        except KeyError as e:
            raise exceptions.DoesNotExistsOnServer from e
        finally:
            cli.close()

    def get_procfile(self, version_info: VersionInfo) -> Dict[str, str]:
        """Read Procfile config from SourcePackage.meta_data(the field stored app_desc) or repository"""
        from paasng.extensions.declarative.handlers import get_desc_handler

        _, version = self.extract_version_info(version_info)
        package_storage = self.module.packages.get(version=version)
        if package_storage.meta_info:
            try:
                handler = get_desc_handler(package_storage.meta_info)
                deploy_desc = handler.get_deploy_desc(self.module.name)
                return deploy_desc.get_procfile()
            except Exception as e:
                raise exceptions.GetProcfileError('unable to read file "Procfile"') from e
        # read procfile from package directly
        return super().get_procfile(version_info)

    def get_app_desc(self, version_info: VersionInfo) -> Dict:
        """Read app.yaml/app_desc.yaml from SourcePackage.meta_data(the field stored app_desc) or repository"""
        _, version = self.extract_version_info(version_info)
        package_storage = self.module.packages.get(version=version)
        if package_storage.meta_info:
            return package_storage.meta_info
        return super().get_app_desc(version_info)


def get_metadata_reader(
    module: 'Module', operator: Optional[str] = None, source_dir: Path = _current_path
) -> MetaDataReader:
    """Get MetaData Reader for the given module
    :param module: 待操作的模块
    :param operator: 操作人, 用于获取鉴权信息
    :param source_dir: 部署目录, 只对 VCS 类型的源码系统生效
    """
    source_origin = module.get_source_origin()
    if source_origin == SourceOrigin.AUTHORIZED_VCS:
        return VCSMetaDataReader(get_repo_controller(module, operator), source_dir=source_dir)
    elif source_origin in [SourceOrigin.BK_LESS_CODE, SourceOrigin.S_MART]:
        return PackageMetaDataReader(module, source_dir)
    elif source_origin == SourceOrigin.IMAGE_REGISTRY:
        raise NotImplementedError("IMAGE_REGISTRY doesn't support read AppDescription")
    elif source_origin == SourceOrigin.SCENE:
        return VCSMetaDataReader(get_repo_controller(module, operator))
    else:
        raise NotImplementedError
