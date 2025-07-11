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

import abc
import datetime
import itertools
import logging
from typing import Any, Dict, Generator, List, Optional, Union

import arrow
import requests
from django.utils.translation import gettext_lazy as _
from oauthlib.oauth2.rfc6749.errors import OAuth2Error

from paasng.infras.accounts.models import Oauth2TokenHolder
from paasng.platform.sourcectl import exceptions
from paasng.platform.sourcectl.models import CommitInfo, GitProject

logger = logging.getLogger(__name__)

# 第一页页码
PAGE_START_AT = 1
# 默认每页数量
DEFAULT_PER_PAGE = 100
# 请求超时时间，单位秒
DEFAULT_TIMEOUT = 90
# 默认 Ref 值（branch），一般为 master 或者 main
DEFAULT_REPO_REF = "master"
# 重试次数
RETRY_TIME = 3


class BaseGitApiClient(abc.ABC):
    """Git 基础 API SDK"""

    api_url: str
    access_token: str
    session: requests.Session
    token_holder: Optional[Oauth2TokenHolder]

    auth_header_key: str = "Authorization"

    @abc.abstractmethod
    def list_repo(self, **kwargs) -> List[Dict]:
        """获取用户的所有仓库"""

    @abc.abstractmethod
    def repo_get_raw_file(self, project: GitProject, filepath: str, ref=DEFAULT_REPO_REF, **kwargs) -> bytes:
        """从远程仓库下载 filepath 的文件

        :param project: 项目对象
        :param filepath: 需要下载的文件路径
        :param ref: commit/branch/tag 值
        :return: 文件内容
        """

    @abc.abstractmethod
    def repo_list_branches(self, project: GitProject, **kwargs) -> List[Dict]:
        """获取指定仓库所有的 branch"""

    @abc.abstractmethod
    def repo_list_tags(self, project: GitProject, **kwargs) -> List[Dict]:
        """获取指定仓库所有 tags"""

    @abc.abstractmethod
    def repo_last_commit(self, project: GitProject, branch_or_hash: Optional[str] = None) -> Dict:
        """获取最后一次 commit 信息

        :param project: 项目对象
        :param branch_or_hash: 分支名或 commit 的 hash 值
        :return: 最新 commit 信息
        """

    @abc.abstractmethod
    def get_user_info(self, username: str) -> Dict:
        """根据用户名查询用户信息"""

    @abc.abstractmethod
    def get_project_info(self, project: GitProject) -> Dict:
        """获取项目详细信息"""

    @abc.abstractmethod
    def list_all_commit_logs(self, project: GitProject) -> Generator[Dict, None, None]:
        """获取全量 commit 信息"""

    @abc.abstractmethod
    def calculate_user_contribution(
        self,
        username: str,
        project: GitProject,
        begin_date: Optional[Union[datetime.datetime, arrow.Arrow]] = None,
        end_date: Optional[Union[datetime.datetime, arrow.Arrow]] = None,
    ) -> Dict:
        """统计贡献"""

    @abc.abstractmethod
    def commit_files(self, project: GitProject, commit_info: CommitInfo) -> Dict:
        """批量提交修改文件"""

    @abc.abstractmethod
    def create_with_member(self, *args, **kwargs):
        """创建代码仓库并添加成员"""

    @abc.abstractmethod
    def create_project(self, *args, **kwargs):
        """创建代码仓库"""

    @abc.abstractmethod
    def delete_project(self, *args, **kwargs):
        """删除在 VCS 上的源码项目"""

    def _fetch_all_items(self, target_url: str, params: Optional[Dict] = None) -> Generator[Dict, None, None]:
        for cur_page in itertools.count(start=PAGE_START_AT):
            items = self._fetch_items(target_url, cur_page, params=params)
            if items:
                yield from items
            else:
                break

    def _fetch_items(
        self, target_url: str, cur_page: int, per_page: int = DEFAULT_PER_PAGE, params: Optional[Dict] = None
    ) -> List[Dict]:
        params = params or {}
        params["page"] = cur_page
        params["per_page"] = per_page
        return self._request_with_retry(target_url, params=params)

    def _request_with_retry(self, target_url, **kwargs) -> Any:
        """requests.get 的封装，当 access_token 过期时会尝试 refresh，然后再重做一次请求

        :param target_url: 目标 URL
        :param kwargs: 请求参数
        :return: response.json()
        """
        kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
        for __ in range(RETRY_TIME):
            raw_resp = self.session.get(target_url, **kwargs)
            try:
                resp = self._validate_resp(raw_resp)
            except exceptions.AccessTokenError:
                self._refresh_token()
                continue
            return resp
        raise exceptions.CallGitApiFailed(_("请求失败"))

    def _validate_resp(self, raw_resp: requests.Response) -> Any:
        """尝试解析 requests.Response，当返回 404, 401 等错误时会抛出对应的异常

        :param raw_resp: requests.request 返回的 Response 对象
        :return: response.json()
        """
        if raw_resp.status_code == 404:
            logger.warning(f"get url `{raw_resp.url}` but 404")
            raise exceptions.RemoteResourceNotFoundError(f"{raw_resp.url} dose not exist on server")
        elif raw_resp.status_code == 401:
            logger.warning(f"get url `{raw_resp.url}` but 401")
            raise exceptions.AccessTokenError("the access_token can not fetch resource")
        elif raw_resp.status_code == 403:
            logging.warning(f"get url `{raw_resp.url}` but 403")
            raise exceptions.AccessTokenForbidden("access token forbidden")
        elif raw_resp.status_code == 504:
            logging.warning(f"get url `{raw_resp.url}` but 504")
            raise exceptions.RequestTimeOutError(_("接口请求超时"))
        elif raw_resp.status_code > 500 and raw_resp.status_code != 504:
            logging.warning(f"get url `{raw_resp.url}` but {raw_resp.status_code}, raw resp: {raw_resp}")
            raise exceptions.RequestError(_("接口请求异常"))

        try:
            return raw_resp.json()
        except Exception:
            raise exceptions.RequestError(_("解析接口返回结果失败"))

    def _refresh_token(self):
        """尝试 refresh token，失败时抛出异常（异常信息应该直接反馈到前端）"""

        # 没有 access_token 就不能 refresh，直接报错
        if self.auth_header_key not in self.session.headers:
            raise exceptions.AccessTokenMissingError("access_token not found")

        # 没有 token holder 也不能 refresh，直接报错
        if not self.token_holder:
            raise exceptions.AccessTokenRefreshError("token holder unset")

        # 假设是 OAuth token 过期, 尝试 refresh token
        logger.info(f"try to refresh token for {self.token_holder.user.username}")
        try:
            self.token_holder.refresh()
        except OAuth2Error:
            logger.error(f"failed to refresh token for {self.token_holder.user.username}")  # noqa: TRY400
            raise exceptions.AccessTokenRefreshError("fail to refresh token")

        # 更新 OAuth token 后更新请求头
        self.session.headers[self.auth_header_key] = f"token {self.token_holder.access_token}"
