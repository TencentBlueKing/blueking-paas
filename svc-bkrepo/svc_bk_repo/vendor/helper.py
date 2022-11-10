# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import logging
import math
from typing import Dict, List, Optional

import curlify
import requests
from requests.auth import HTTPBasicAuth
from six.moves.urllib_parse import urljoin
from svc_bk_repo.vendor.exceptions import RequestError
from svc_bk_repo.vendor.models import RepoQuota

logger = logging.getLogger(__name__)


def _validate_resp(response: requests.Response) -> Dict:
    """校验响应体"""
    try:
        logger.info("Equivalent curl command: %s", curlify.to_curl(response.request))
    except Exception:
        pass

    try:
        data = response.json()
    except Exception as e:
        logger.exception("未知错误, %s", response.content)
        raise RequestError(str(e), code="Unknown", response=response) from e

    if data["code"] != 0:
        raise RequestError(data["message"], code=data["code"], response=response)
    return data.get("data", {})


class BKGenericRepoManager:
    """蓝鲸通用二进制仓库."""

    def __init__(
        self,
        endpoint_url: str,
        project: str,
        username: str,
        password: str,
    ):
        # endpoint can not endswith '/'
        self.endpoint_url = endpoint_url.rstrip("/")
        self.project = project
        self.username = username
        self.password = password

    def get_client(self) -> requests.Session:
        session = requests.session()
        session.auth = HTTPBasicAuth(username=self.username, password=self.password)
        return session

    def create_user(self, repo: str, username: str, password: str, association_users: List[str]):
        """创建用户到仓库管理员

        :params username str: 用户名
        :params password str: 密码
        :params association_users List[str]: 关联的真实用户
        :params repo str: 关联的仓库名称
        """
        client = self.get_client()
        url = urljoin(self.endpoint_url, '/auth/api/user/create/repo')
        data = {
            "admin": False,
            "name": username,
            "pwd": password,
            "userId": username,
            "asstUsers": association_users,
            "group": False,
            "projectId": self.project,
            "repoName": repo,
        }
        return _validate_resp(client.post(url, json=data))

    def update_user(self, username: str, password: str, association_users: List[str]):
        """更新用户信息"""
        client = self.get_client()
        url = urljoin(self.endpoint_url, f'/auth/api/user/{username}')
        data = {"admin": True, "name": username, "pwd": password, "asstUsers": association_users}
        return _validate_resp(client.put(url, json=data))

    def delete_user(self, username: str):
        """删除用户"""
        client = self.get_client()
        url = urljoin(self.endpoint_url, f'/auth/api/user/{username}')
        return _validate_resp(client.delete(url))

    def create_repo(self, repo: str, public: bool = False, quota: Optional[int] = None):
        """创建仓库

        :params repo str: 仓库名
        :params public bool: 仓库是否可公开读
        :params quota Optional[int]: 仓库配额, 单位字节
        """
        client = self.get_client()
        url = urljoin(self.endpoint_url, '/repository/api/repo/create')
        data = {
            "projectId": self.project,
            "name": repo,
            "type": "GENERIC",
            "category": "LOCAL",
            "public": public,
            "description": "no description",
            "configuration": None,
            "storageCredentialsKey": None,
            "quota": quota,
        }
        return _validate_resp(client.post(url, json=data))

    def delete_repo(self, repo: str, forced: bool = False):
        """删除仓库

        :params repo str: 仓库名
        :params forced bool: 是否强制删除, 如果为false，当仓库中存在文件时，将无法删除仓库
        """
        client = self.get_client()
        url = urljoin(self.endpoint_url, f'/repository/api/repo/delete/{self.project}/{repo}?forced={forced}')
        return _validate_resp(client.delete(url))

    def get_repo_quota(self, repo: str) -> RepoQuota:
        """查询仓库配额

        :params repo str: 仓库名
        """
        client = self.get_client()
        url = urljoin(self.endpoint_url, f'/repository/api/repo/quota/{self.project}/{repo}')
        data = _validate_resp(client.get(url))
        return RepoQuota(max_size=data["quota"] or math.inf, used=data["used"])

    def update_repo_quota(self, repo: str, quota: int):
        """修改仓库配额

        :params repo str: 仓库名
        :params quota int: 配额, 单位字节
        """
        client = self.get_client()
        url = urljoin(self.endpoint_url, f'/repository/api/repo/quota/{self.project}/{repo}')
        _validate_resp(client.post(url, data={"quota": quota}))
