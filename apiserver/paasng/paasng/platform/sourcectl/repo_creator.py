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
from typing import Dict, Optional, Protocol
from urllib.parse import quote, urljoin, urlparse

import requests
from django.utils.translation import gettext_lazy as _
from requests import models
from requests.auth import AuthBase
from requests.models import Response

from paasng.platform.sourcectl.constants import TcGitMemberRole, TcGitVisibleLevel
from paasng.platform.sourcectl.entities import TcGitRepoProject
from paasng.platform.sourcectl.exceptions import AuthTokenMissingError, RepoNameConflict, TcGitAPIError
from paasng.platform.sourcectl.models import GitProject
from paasng.utils.text import remove_prefix, remove_suffix

logger = logging.getLogger(__name__)


class RepoCreator(Protocol):
    def __init__(self, repository_group: str, api_url: str, user_credentials: Dict): ...

    def create_repo_and_add_member(self, *args, **kwargs):
        """在 VCS 服务创建源码项目并添加成员"""

    def create_project(self, *args, **kwargs):
        """在 VCS 服务创建源码项目"""

    def delete_project(self, *args, **kwargs):
        """删除在 VCS 上的源码项目"""

    def add_member(self, *args, **kwargs):
        """添加仓库成员"""

    def remove_member(self, *args, **kwargs):
        """移除仓库成员"""


class TcGitAuth(AuthBase):
    """腾讯工蜂 API auth 请求头"""

    def __init__(self, oauth_token: Optional[str] = None, private_token: Optional[str] = None):
        auth_headers = {}
        if oauth_token:
            auth_headers["OAUTH-TOKEN"] = oauth_token
        if private_token:
            auth_headers["PRIVATE-TOKEN"] = private_token
        if not auth_headers:
            raise AuthTokenMissingError("invalid user credentials")
        self._auth_headers = auth_headers

    def __call__(self, r: models.PreparedRequest) -> models.PreparedRequest:
        r.headers.update(self._auth_headers)
        return r


def validate_response(resp: Response) -> Response:
    if resp.status_code == 404:
        logger.warning(f"get url `{resp.url}` but 404")
        raise TcGitAPIError(f"{resp.url} dose not exist on server")
    elif resp.status_code == 401:
        logger.warning(f"get url `{resp.url}` but 401")
        raise TcGitAPIError("the access_token can not fetch resource")
    elif resp.status_code == 403:
        logging.warning(f"get url `{resp.url}` but 403")
        raise TcGitAPIError("access token forbidden")
    elif resp.status_code == 504:
        logging.warning(f"get url `{resp.url}` but 504")
        raise TcGitAPIError(_("工蜂接口请求超时"))
    elif resp.status_code > 500 and resp.status_code != 504:
        logging.warning(f"get url `{resp.url}` but {resp.status_code}, raw resp: {resp}")
        raise TcGitAPIError(_("工蜂接口请求异常"))
    elif not resp.ok:
        message = resp.json()["message"]
        if message == '400 bad request for {:path=>["Path has already been taken"]}':
            raise RepoNameConflict(message)
        logging.warning(f"get url `{resp.url}` but resp is not ok, raw resp: {resp}")
        raise TcGitAPIError(message)
    return resp


class TcGitRepoCreator:
    """实现工蜂代码仓库创建、成员管理等核心操作"""

    def __init__(self, repository_group: str, api_url: str, user_credentials: Dict):
        """初始化仓库管理器
        :param repository_group: 仓库组地址
        :param api_url: 仓库API地址
        :param user_credentials: 用户认证信息
        """
        self.repository_group = repository_group
        self._api_url = api_url
        self._session = requests.session()
        self._session.auth = TcGitAuth(**user_credentials)
        self._namespace = remove_suffix(remove_prefix(urlparse(self.repository_group).path, "/groups/"), "/")

    def create_repo_and_add_member(
        self,
        repo_name: str,
        description: str,
        username: str,
        visibility_level: TcGitVisibleLevel = TcGitVisibleLevel.PUBLIC,
        role: TcGitMemberRole = TcGitMemberRole.MASTER,
    ) -> str:
        """创建代码仓库并添加成员

        :param repo_name: 源码仓库名称
        :param description: 仓库描述
        :param username: 需要添加的成员用户名
        :param visibility_level: 仓库可见范围，默认为 public
        :param role: 成员角色权限，默认为 master
        :return: 创建的代码仓库的地址
        """
        project = self.create_project(repo_name, visibility_level, description)
        self.add_member(project.repo_url, username, role)
        return project.repo_url

    def create_project(
        self, repo_name: str, visibility_level: TcGitVisibleLevel, description: str
    ) -> TcGitRepoProject:
        """为插件在 VCS 服务创建源码项目
        :param repo_name: 源码仓库名称
        :param visibility_level: 仓库可见范围
        :param description: 仓库描述
        """

        _url = "api/v3/projects"
        resp = self._session.post(
            urljoin(self._api_url, _url),
            data={
                "name": repo_name,
                "namespace_id": self._get_namespace_id(),
                "description": description,
                "visibility_level": visibility_level,
            },
        )
        validate_response(resp)

        project_info = resp.json()
        return TcGitRepoProject(id=project_info["id"], repo_url=project_info["http_url_to_repo"])

    def delete_project(self, repo_url: str):
        """删除在 VCS 上的源码项目
        :param repo_url: 源码仓库地址
        """
        git_project = GitProject.parse_from_repo_url(repo_url, "tc_git")
        _id = quote(git_project.path_with_namespace, safe="")
        _url = f"api/v3/projects/{_id}"
        resp = self._session.delete(urljoin(self._api_url, _url))
        validate_response(resp)

    def add_member(self, repo_url: str, username: str, role: TcGitMemberRole):
        """添加仓库成员"""
        _id = self._get_repo_id(repo_url)
        _url = f"api/v3/projects/{_id}/members"
        data = {"user_id": self._get_user_id(username), "access_level": role}
        self._session.post(urljoin(self._api_url, _url), data=data)

    def remove_member(self, repo_url: str, username: str):
        """移除仓库成员"""
        _id = self._get_repo_id(repo_url)
        _url = f"api/v3/projects/{_id}/members/{self._get_user_id(username)}"
        self._session.delete(urljoin(self._api_url, _url))

    def _get_repo_id(self, repo_url: str) -> str:
        """根据仓库地址获取仓库 ID"""
        git_project = GitProject.parse_from_repo_url(repo_url, "tc_git")
        return quote(git_project.path_with_namespace, safe="")

    def _get_namespace_id(self) -> int:
        """获取 groups 的命名空间 id"""
        _url = f"api/v3/groups/{quote(self._namespace, safe='')}"
        resp = self._session.get(urljoin(self._api_url, _url))
        validate_response(resp)
        return resp.json()["id"]

    def _get_user_id(self, username: str) -> int:
        """根据用户名获取 user_id"""
        _url = f"api/v3/users/{username}"
        resp = self._session.get(urljoin(self._api_url, _url))
        return validate_response(resp).json()["id"]
