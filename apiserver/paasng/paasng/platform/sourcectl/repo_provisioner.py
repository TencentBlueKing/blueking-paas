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

from typing import Dict, List, Optional

from typing_extensions import Protocol

from paasng.infras.accounts.utils import get_oauth_credentials
from paasng.platform.sourcectl.models import GitGroup
from paasng.platform.sourcectl.source_types import get_sourcectl_type


class RepoProvisioner(Protocol):
    """处理仓库管理操作（创建仓库、添加成员等）的功能类"""

    @classmethod
    def init_by_platform_account(cls, source_type: str):
        """Return a RepoController object from given source_type from platform account

        :param source_type: Code repository type, such as github
        :param repo_url: repository url
        """
        raise NotImplementedError

    @classmethod
    def init_by_user(cls, source_type: str, user_id: str):
        """Return a RepoController object from user's authorization credentials

        :param source_type: Code repository type, such as github
        :param repo_url: repository url
        :param user_id: current operator's user_id
        """
        raise NotImplementedError

    @classmethod
    def list_owned_groups(cls, api_url: str, user_credentials: dict) -> List[GitGroup]:
        """获取有 owner 权限的项目组列表"""
        raise NotImplementedError

    def create_with_member(self, *args, **kwargs):
        """创建代码仓库并添加成员"""

    def create_project(self, *args, **kwargs):
        """创建代码仓库"""

    def delete_project(self, *args, **kwargs):
        """删除在 VCS 上的源码项目"""


class BaseGitProvisioner:
    """Git 仓库管理基类"""

    def __init__(self, api_url: str, user_credentials: Optional[Dict] = None):
        pass

    @classmethod
    def init_by_platform_account(cls, source_type: str):
        """Return a RepoController object from public account configured through the platform

        :param source_type: Code repository type, such as github
        :param repo_url: repository url
        """
        source_config = get_sourcectl_type(source_type).config_as_arguments()
        if "api_url" not in source_config or "bkpaas_private_token" not in source_config:
            raise ValueError("Require api_url and bkpaas_private_token to init GitRepoController")

        user_credentials = {"private_token": source_config["bkpaas_private_token"], "scope_list": []}
        return cls(api_url=source_config["api_url"], user_credentials=user_credentials)

    @classmethod
    def init_by_user(cls, source_type: str, user_id: str):
        """Return a RepoController object from user's authorization credentials

        :param source_type: Code repository type, such as github
        :param user_id: current operator's user_id
        """
        source_config = get_sourcectl_type(source_type).config_as_arguments()
        if "api_url" not in source_config:
            raise ValueError("Require api_url to init GitRepoController")

        user_credentials = get_oauth_credentials(source_type, user_id)
        return cls(api_url=source_config["api_url"], user_credentials=user_credentials)


def list_all_owned_groups(source_type: str, user_id: str) -> List[GitGroup]:
    """获取用户在指定源码控制类型下的所有 owner 权限的项目组

    :param source_type: 源码控制类型，如 gitlab
    :param user_id: 用户 ID，用于查询用户对应的授权凭证
    """
    repo_provisioner_class = get_sourcectl_type(source_type).repo_provisioner_class
    if not repo_provisioner_class:
        raise ValueError(f"Source type {source_type} not support list repository groups")

    user_credentials = get_oauth_credentials(source_type, user_id)
    type_spec = get_sourcectl_type(source_type)
    source_config = type_spec.config_as_arguments()
    return repo_provisioner_class.list_owned_groups(source_config["api_url"], user_credentials)
