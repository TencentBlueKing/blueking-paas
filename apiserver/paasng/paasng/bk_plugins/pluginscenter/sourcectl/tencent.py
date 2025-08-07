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
from textwrap import dedent
from typing import Dict, Iterator, List, Optional, Union
from urllib.parse import quote, urljoin, urlparse

import arrow
import requests
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from requests import models
from requests.auth import AuthBase
from requests.models import Response

from paasng.bk_plugins.pluginscenter.constants import PluginRole
from paasng.bk_plugins.pluginscenter.definitions import PluginCodeTemplate
from paasng.bk_plugins.pluginscenter.features import PluginFeatureFlag, PluginFeatureFlagsManager
from paasng.bk_plugins.pluginscenter.models import PluginDefinition, PluginInstance
from paasng.bk_plugins.pluginscenter.sourcectl.base import AlternativeVersion, TemplateRender, generate_context
from paasng.bk_plugins.pluginscenter.sourcectl.exceptions import (
    APIError,
    AuthTokenMissingError,
    PluginRepoNameConflict,
)
from paasng.bk_plugins.pluginscenter.sourcectl.git import GitTemplateDownloader
from paasng.platform.sourcectl.git.client import GitClient, MutableURL
from paasng.platform.sourcectl.models import GitProject
from paasng.platform.sourcectl.utils import generate_temp_dir
from paasng.utils.text import remove_prefix, remove_suffix

logger = logging.getLogger(__name__)


class TencentGitAuth(AuthBase):
    """TencentGit api auth handler"""

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
        raise APIError(f"{resp.url} dose not exist on server")
    elif resp.status_code == 401:
        logger.warning(f"get url `{resp.url}` but 401")
        raise APIError("the access_token can not fetch resource")
    elif resp.status_code == 403:
        logging.warning(f"get url `{resp.url}` but 403")
        raise APIError("access token forbidden")
    elif resp.status_code == 504:
        logging.warning(f"get url `{resp.url}` but 504")
        raise APIError(_("工蜂接口请求超时"))
    elif resp.status_code > 500 and resp.status_code != 504:
        logging.warning(f"get url `{resp.url}` but {resp.status_code}, raw resp: {resp}")
        raise APIError(_("工蜂接口请求异常"))
    elif not resp.ok:
        message = resp.json()["message"]
        if message == '400 bad request for {:path=>["Path has already been taken"]}':
            raise PluginRepoNameConflict(message)
        logging.warning(f"get url `{resp.url}` but resp is not ok, raw resp: {resp}")
        raise APIError(message)
    return resp


class PluginRepoAccessor:
    """PluginRepoAccessor implement with TencentGit"""

    def __init__(self, plugin: PluginInstance, api_url: str, user_credentials: Dict):
        self.plugin = plugin
        self.project = GitProject.parse_from_repo_url(plugin.repository, "tc_git")
        self._api_url = api_url
        self._session = requests.session()
        self._session.auth = TencentGitAuth(**user_credentials)
        self._user_credentials = user_credentials

    def extract_smart_revision(self, smart_revision: str) -> str:
        """将有名字的版本号（Named Version）转换成更具体的版本号, 例如，将 Git 的 master 分支转换成 SHA Commit ID

        :param smart_revision: 有名字的版本号，比如 master
        """
        if ":" not in smart_revision:
            return smart_revision
        _, version_name = smart_revision.split(":")
        commit = self.get_last_commit(self.project, version_name)
        return commit["id"]

    def list_alternative_versions(
        self, include_branch: bool = True, include_tag: bool = True
    ) -> List[AlternativeVersion]:
        """列举当前所有可选的有名字的版本号，通常包括 branch, tag 等"""
        result = []
        if include_branch:
            for branch in self.list_branches(self.project):
                result.append(self._branch_data_to_version("branch", branch))
        if include_tag:
            for tag in self.list_tags(self.project):
                result.append(self._branch_data_to_version("tag", tag))
        return sorted(result, key=lambda item: item.last_update, reverse=True)  # type: ignore

    def get_submit_info(self, begin_time: str, end_time: str) -> List[dict]:
        """查询项目的提交次数、提交用户数，默认统计全部分支的统计情况
        : param begin_time: 开始时间；例如 2019-03-25T00:10:19+0000
        : param end_time: 结束时间：例如 2019-03-26T00:10:19+0000
        """
        _id = quote(self.project.path_with_namespace, safe="")
        _url = f"api/v3/projects/{_id}/tloc/daily/count"
        # 指定你的当前时区，默认是 0 时区，范围 (-11,11)
        time_zone_num = int(timezone.localtime().tzinfo.utcoffset(timezone.now()).seconds / 3600)

        params: Dict[str, Union[str, int]] = dict(begin_date=begin_time, end_date=end_time, timezone=time_zone_num)
        resp = self._session.get(urljoin(self._api_url, _url), params=params)

        try:
            return validate_response(resp).json()
        except APIError:
            # 工蜂 API 异常时，记录日志，并给前端返回空数组，避免页面展示异常
            # 查询同一天的代码提交记录 API 会报错，看工蜂自己的统计页面是直接返回空数据，没有限制用户的时间选择，我们也使用同样的处理逻辑
            return []

    def list_branches(self, project: GitProject, **kwargs) -> List[dict]:
        """获取仓库的所有 branches
        :param project: 项目对象
        :return: 包含 branch 字典的列表
        """
        _id = quote(project.path_with_namespace, safe="")
        _url = f"api/v3/projects/{_id}/repository/branches"
        return list(self._fetch_all_item(urljoin(self._api_url, _url)))

    def list_tags(self, project: GitProject, **kwargs) -> List[dict]:
        """获取仓库的所有 tags
        :param project: 项目对象
        :return: 包含 tag 字典的列表
        """
        _id = quote(project.path_with_namespace, safe="")
        _url = f"api/v3/projects/{_id}/repository/tags"
        return list(self._fetch_all_item(urljoin(self._api_url, _url)))

    def get_last_commit(self, project: GitProject, name_or_hash) -> Dict:
        """获取最后一次 commit 的内容
        :param project: 项目对象
        :param name_or_hash: commit hash 值、分支名或 tag
        :return: 包含 commit 内容的字典
        """
        _id = quote(project.path_with_namespace, safe="")
        _url = f"api/v3/projects/{_id}/repository/commits/{quote(name_or_hash, safe='')}"
        resp = self._session.get(urljoin(self._api_url, _url))
        return validate_response(resp).json()

    def _fetch_all_item(self, target_url, params=None) -> Iterator[Dict]:
        cur_page = 0
        while True:
            cur_page += 1
            tmp = self._fetch_items(target_url, cur_page, per_page=100, params=params)
            if len(tmp) > 0:
                yield from tmp
            else:
                break

    def _fetch_items(self, target_url, cur_page, per_page=100, params=None) -> List[dict]:
        """工蜂每个接口，最大只能获取 100 条记录
        :param target_url:
        :param cur_page: 当前页面
        """
        params = params or {}
        default_params = dict(page=cur_page, per_page=per_page)
        default_params.update(params)
        resp = self._session.get(target_url, params=default_params).json()
        assert isinstance(resp, (list, tuple)), f"got a wrong type of resp {type(resp)}, which contained {resp}"
        return resp  # type: ignore

    def _branch_data_to_version(self, data_source: str, data: Dict) -> AlternativeVersion:
        """[private] transform a git branch data to an AlternativeVersion object

        :param data_source: tag or branch
        :param data: JSON data returned from gitlab api
        """
        if data_source not in ("tag", "branch"):
            raise ValueError("type must be tag or branch")
        try:
            message = data["message"]
        except KeyError:
            message = data["commit"]["message"]

        date_str = data["commit"]["committed_date"]
        # Convert local time to utc datetime
        commit_date = arrow.get(date_str).to("utc").datetime
        return AlternativeVersion(
            name=data["name"],
            type=data_source,
            revision=data["commit"]["id"],
            url=self.plugin.repository,
            last_update=commit_date,
            message=message,
        )

    def build_compare_url(self, from_revision: str, to_revision: str) -> str:
        repo_url = self.plugin.repository
        from_revision = self.extract_smart_revision(from_revision)
        to_revision = self.extract_smart_revision(to_revision)
        return repo_url.replace(".git", f"/compare/{from_revision}...{to_revision}")

    def get_project_id(self) -> int:
        """获取工蜂仓库的项目ID"""
        _id = quote(self.project.path_with_namespace, safe="")
        _url = f"api/v3/projects/{_id}"
        resp = self._session.get(urljoin(self._api_url, _url))
        validate_response(resp)
        return resp.json()["id"]


class PluginRepoInitializer:
    """PluginRepoInitializer implement with TencentGit"""

    def __init__(self, pd: PluginDefinition, api_url: str, user_credentials: Dict):
        self.repository_group = pd.basic_info_definition.repository_group
        self._api_url = api_url
        self._session = requests.session()
        self._session.auth = TencentGitAuth(**user_credentials)
        self._client = GitClient()
        self._template_render = TemplateRender(GitTemplateDownloader(self._client))
        self._namespace = remove_suffix(remove_prefix(urlparse(self.repository_group).path, "/groups/"), "/")
        self._user_credentials = user_credentials

    def create_project(self, plugin: PluginInstance):
        """为插件在 VCS 服务创建源码项目"""
        repo_name = plugin.id
        if PluginFeatureFlagsManager(plugin).has_feature(PluginFeatureFlag.LOWER_REPO_NAME):
            repo_name = repo_name.lower()

        _url = "api/v3/projects"
        resp = self._session.post(
            urljoin(self._api_url, _url),
            data={
                "name": repo_name,
                "namespace_id": self._get_namespace_id(),
                "description": plugin.name,
                "visibility_level": settings.PLUGIN_VISIBILTY_LEVEL,
            },
        )
        validate_response(resp)

        project_info = resp.json()
        plugin.repository = project_info["http_url_to_repo"]
        plugin.save(update_fields=["repository", "updated"])
        self._enable_ci(project_info["id"])
        return project_info

    def delete_project(self, plugin: PluginInstance):
        """删除插件在 VCS 上的源码项目"""
        git_project = GitProject.parse_from_repo_url(plugin.repository, "tc_git")
        _id = quote(git_project.path_with_namespace, safe="")
        _url = f"api/v3/projects/{_id}"
        resp = self._session.delete(urljoin(self._api_url, _url))
        validate_response(resp)

    def initial_repo(self, plugin: PluginInstance):
        """初始化插件代码"""
        git_project = GitProject.parse_from_repo_url(plugin.repository, "tc_git")
        context = generate_context(plugin)
        with generate_temp_dir() as dest_dir:
            # git clone <repository> <dest_dir>
            self._client.clone(self._build_repo_url_with_auth(git_project), dest_dir)
            # render <template> to <dest_dir>
            self._template_render.render(self._get_accessible_template(plugin), dest_dir, context=context)
            # git add .
            self._client.add(dest_dir, Path("."))
            self._fix_git_user_config(dest_dir / ".git" / "config")
            # git commit -m "init repo"
            self._client.commit(dest_dir, message="feat: init repo")
            # git push
            self._client.push(dest_dir)

    def _get_accessible_template(self, plugin: PluginInstance) -> PluginCodeTemplate:
        """获取可访问的模板地址"""
        template = plugin.template.copy(deep=True)
        if urlparse(template.repository).hostname in ["github.com", "git.tencent.com"]:
            return template
        git_project = GitProject.parse_from_repo_url(template.repository, "tc_git")
        template.repository = str(self._build_repo_url_with_auth(git_project))
        return template

    def _fix_git_user_config(self, dest_dir: Path):
        """修复 git 的用户信息缺失问题"""
        with dest_dir.open(mode="a") as fh:
            fh.write(
                dedent(
                    f"""
            [user]
                email = {settings.PLUGIN_REPO_CONF["email"]}
                name = {settings.PLUGIN_REPO_CONF["username"]}
            """
                )
            )

    def _build_repo_url_with_auth(self, project: GitProject) -> MutableURL:
        """构建包含 username:oauth_token 的 repo url"""
        if not self._user_credentials:
            raise AuthTokenMissingError("private_token or oauth_token required")

        private_token = self._user_credentials.get("private_token")
        oauth_token = self._user_credentials.get("oauth_token")
        if not private_token and not oauth_token:
            raise AuthTokenMissingError("private_token or oauth_token required")

        if private_token:
            username = "private"
            password = private_token
        else:
            username = "oauth2"
            password = oauth_token

        return MutableURL(urljoin(self._api_url, project.path_with_namespace)).replace(
            username=quote(username), password=quote(password)
        )

    def _get_namespace_id(self) -> int:
        """获取 groups 的命名空间 id"""
        _url = f"api/v3/groups/{quote(self._namespace, safe='')}"
        resp = self._session.get(urljoin(self._api_url, _url))
        validate_response(resp)
        return resp.json()["id"]

    def _enable_ci(self, project_id: int):
        """开启工蜂 CI 特性"""
        _url = f"api/v3/projects/{project_id}/ci/enable"
        resp = self._session.put(urljoin(self._api_url, _url), params={"enable_ci": True})
        validate_response(resp)


class PluginRepoMemberMaintainer:
    """PluginRepoMemberMaintainer implement with TencentGit"""

    def __init__(self, plugin: PluginInstance, api_url: str, user_credentials: Dict):
        self.project = GitProject.parse_from_repo_url(plugin.repository, "tc_git")
        self._api_url = api_url
        self._session = requests.session()
        self._session.auth = TencentGitAuth(**user_credentials)

    def add_member(self, username: str, role: PluginRole = PluginRole.DEVELOPER):
        """添加仓库成员"""
        _id = quote(self.project.path_with_namespace, safe="")
        _url = f"api/v3/projects/{_id}/members"
        data = {"user_id": self._get_user_id(username), "access_level": 40 if role == PluginRole.ADMINISTRATOR else 30}
        self._session.post(urljoin(self._api_url, _url), data=data)

    def remove_member(self, username: str):
        """移除仓库成员"""
        _id = quote(self.project.path_with_namespace, safe="")
        _url = f"api/v3/projects/{_id}/members/{self._get_user_id(username)}"
        self._session.delete(urljoin(self._api_url, _url))

    def _get_user_id(self, username: str) -> int:
        """根据用户名获取 user_id"""
        _url = f"api/v3/users/{username}"
        resp = self._session.get(urljoin(self._api_url, _url))
        return validate_response(resp).json()["id"]
