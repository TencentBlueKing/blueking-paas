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
import abc
import logging
from os import PathLike
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type, Union

from bkpaas_auth.core.encoder import ProviderType, user_id_encoder
from typing_extensions import Protocol

from paasng.infras.accounts.models import Oauth2TokenHolder, PrivateTokenHolder, UserProfile
from paasng.platform.sourcectl import exceptions
from paasng.platform.sourcectl.models import AlternativeVersion, CommitLog, GitProject, Repository, VersionInfo
from paasng.platform.sourcectl.source_types import get_sourcectl_type
from paasng.platform.modules.constants import SourceOrigin

if TYPE_CHECKING:
    from paasng.platform.modules.models import Module

logger = logging.getLogger(__name__)


class RepoController(Protocol):
    """RepoController 是一种用于操作源码仓库的对象，主要功能包括读取某个（特定版本的）文件内容、导出仓库、
    列举所有版本号以及获取可访问的对比源码差异的地址等。

    定义在 type_specs 里的不同源码仓库类型，通常拥有各自不同的 RepoController 实现。
    """

    @classmethod
    def init_by_module(cls, module: 'Module', operator: Optional[str] = None):
        """Return a RepoController object from given module and repo_url

        :param module: Module
        :param operator: current operator's user_id, the credentials for fetching source files will
            be extracted from this user. eg. oauth2 token for git repositories.
        """
        raise NotImplementedError

    @classmethod
    def list_all_repositories(cls, **kwargs) -> List[Repository]:
        """返回当前 RepoController 可以控制的所有仓库列表"""

    def touch(self) -> bool:
        """尝试访问远程仓库, 试探是否有访问权限

        :return: 是否有权限
        """

    def export(self, local_path: PathLike, version_info: VersionInfo):
        """导出指定版本的整个项目内容到本地路径

        :param local_path: 本地路径
        :param version_info: 指定版本信息
        """

    def build_url(self, version_info: VersionInfo) -> str:
        """拼接生成指定版本的项目源码的可访问地址

        :param version_info: 指定版本信息
        """

    def build_compare_url(self, from_revision: str, to_revision: str) -> str:
        """获取可访问的对比源码差异的访问链接"""

    def extract_version_info(self, version_info: VersionInfo) -> Tuple[str, str]:
        """解析某个 VersionInfo 对象

        :return: 元组（version_name, revision），前者是有名字的版本号，比如 master，后者为具体的
            Commit ID。
        """

    def extract_smart_revision(self, smart_revision: str) -> str:
        """将有名字的版本号（Named Version）转换成更具体的版本号, 例如，将 Git 的 master 分支转换成 SHA Commit ID

        :param smart_revision: 有名字的版本号，比如 master
        """

    def list_alternative_versions(self) -> List[AlternativeVersion]:
        """列举当前所有可选的有名字的版本号，通常包括 branch, tag 等"""

    def get_diff_commit_logs(self, from_revision: str, to_revision: str, rel_filepath=None) -> List[CommitLog]:
        """读取 from_revision 至 to_revision 关于 rel_filepath 的所有 commit 日志条目"""

    @abc.abstractmethod
    def read_file(self, file_path: str, version_info: VersionInfo) -> bytes:
        """从当前仓库指定版本(version_info)的代码中读取指定文件(file_path) 的内容

        :raises: exceptions.DoesNotExistsOnServer
        """


class BaseGitRepoController:
    """Git RepoController 基类"""

    def __init__(self, api_url: str, repo_url: Optional[str], user_credentials: Optional[Dict] = None):
        pass

    def get_client(self):
        raise NotImplementedError

    @classmethod
    def init_by_module(cls, module: 'Module', operator: Optional[str] = None):
        repo_info = get_sourcectl_type(module.source_type).config_as_arguments(module.region)
        repo_url = module.get_source_obj().get_repo_url()
        if not repo_url:
            raise ValueError("Require repo_url to init GitRepoController")
        project = GitProject.parse_from_repo_url(repo_url, sourcectl_type=module.source_type)
        user_credentials = cls.get_user_credentials(project, operator or module.owner)
        return cls(repo_url=repo_url, user_credentials=user_credentials, api_url=repo_info["api_url"])

    @classmethod
    def get_user_credentials(cls, project: GitProject, operator: str) -> Dict[str, Any]:
        """get user_credentials used to init git client by encoded username"""
        user_credentials: Dict[str, Any] = {}
        provider_type, _ = user_id_encoder.decode(operator)
        try:
            profile = UserProfile.objects.get(user=operator)
        except UserProfile.DoesNotExist:
            raise exceptions.UserNotBindedToSourceProviderError(project=project)
        token_holder: Union[PrivateTokenHolder, Oauth2TokenHolder]
        if provider_type == ProviderType.DATABASE:
            try:
                token_holder = profile.private_token_holder.get_by_project(project)
                user_credentials["private_token"] = token_holder.private_token
            except PrivateTokenHolder.DoesNotExist:
                raise exceptions.UserNotBindedToSourceProviderError(project=project)
        else:
            try:
                token_holder = profile.token_holder.get_by_project(project)
                user_credentials["oauth_token"] = token_holder.access_token
            except Oauth2TokenHolder.DoesNotExist:
                raise exceptions.UserNotBindedToSourceProviderError(project=project)
        user_credentials["scope_list"] = [token_holder.get_scope()]
        # 用于 refresh token, 通过 oauth_token 无法反查 token_holder
        user_credentials["__token_holder"] = token_holder
        return user_credentials


def get_repo_controller_cls(source_origin: Union[int, SourceOrigin], source_control_type) -> Type[RepoController]:
    source_origin = SourceOrigin(source_origin)
    if source_origin not in [SourceOrigin.AUTHORIZED_VCS, SourceOrigin.SCENE]:
        raise NotImplementedError

    return get_sourcectl_type(source_control_type).repo_controller_class


def get_repo_controller(module: 'Module', operator: Optional[str] = None) -> RepoController:
    cls = get_repo_controller_cls(module.get_source_origin(), module.source_type)
    return cls.init_by_module(module, operator)


def list_git_repositories(source_control_type: str, operator: str) -> List[Repository]:
    cls = get_sourcectl_type(source_control_type).repo_controller_class

    profile = UserProfile.objects.get(user=operator)
    token_holder_list = profile.token_holder.filter(provider=source_control_type).all()
    if not token_holder_list:
        raise Oauth2TokenHolder.DoesNotExist

    # 目前工蜂不限制 token 拉取项目列表, 因此简化这里的逻辑只取一个 token
    token_holder = token_holder_list[0]
    user_credentials = {
        "oauth_token": token_holder.access_token,
        "scope_list": [token_holder.get_scope() for token_holder in token_holder_list],
    }

    type_spec = get_sourcectl_type(source_control_type)
    repo_info = type_spec.config_as_arguments(None)
    return cls.list_all_repositories(**user_credentials, **repo_info)
