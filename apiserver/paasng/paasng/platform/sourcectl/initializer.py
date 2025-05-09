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
from pathlib import Path
from textwrap import dedent
from typing import Dict, Optional, Protocol
from urllib.parse import quote, urljoin, urlparse

import requests
from cookiecutter.main import cookiecutter
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from requests import models
from requests.auth import AuthBase
from requests.models import Response

from paasng.platform.modules.models import Module
from paasng.platform.modules.utils import get_module_init_repo_context
from paasng.platform.sourcectl.connector import get_repo_connector
from paasng.platform.sourcectl.constants import TencentGitMemberRole, TencentGitVisibleLevel
from paasng.platform.sourcectl.definitions import RepoProject
from paasng.platform.sourcectl.exceptions import APIError, AuthTokenMissingError, RepoNameConflict
from paasng.platform.sourcectl.git.client import GitClient, MutableURL
from paasng.platform.sourcectl.models import GitProject
from paasng.platform.sourcectl.source_types import get_sourcectl_type
from paasng.platform.sourcectl.utils import generate_temp_dir
from paasng.platform.templates.constants import TemplateType
from paasng.platform.templates.models import Template
from paasng.platform.templates.templater import Templater
from paasng.utils.text import remove_prefix, remove_suffix

logger = logging.getLogger(__name__)


class RepoInitializer(Protocol):
    def __init__(self, repository_group: str, api_url: str, user_credentials: Dict): ...

    def create_project(self, *args, **kwargs):
        """为插件在 VCS 服务创建源码项目"""

    def delete_project(self, *args, **kwargs):
        """删除插件在 VCS 上的源码项目"""

    def initial_repo(self, *args, **kwargs):
        """初始化插件代码"""

    def add_member(self, *args, **kwargs):
        """添加仓库成员"""

    def remove_member(self, *args, **kwargs):
        """移除仓库成员"""


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
            raise RepoNameConflict(message)
        logging.warning(f"get url `{resp.url}` but resp is not ok, raw resp: {resp}")
        raise APIError(message)
    return resp


class TcGitRepoInitializer:
    """工蜂仓库初始化器，实现仓库创建、初始化、成员管理等核心操作"""

    def __init__(self, repository_group: str, api_url: str, user_credentials: Dict):
        """初始化仓库管理器

        :param repository_group: 仓库组地址
        :param api_url: 仓库API地址
        :param user_credentials: 用户认证信息
        """
        self.repository_group = repository_group
        self._api_url = api_url
        self._session = requests.session()
        self._session.auth = TencentGitAuth(**user_credentials)
        self._client = GitClient()
        self._namespace = remove_suffix(remove_prefix(urlparse(self.repository_group).path, "/groups/"), "/")
        self._user_credentials = user_credentials

    def create_project(
        self, repo_name: str, visibility_level: TencentGitVisibleLevel, description: str
    ) -> RepoProject:
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
        return RepoProject(id=project_info["id"], repo_url=project_info["http_url_to_repo"])

    def delete_project(self, repo_url: str):
        """删除在 VCS 上的源码项目

        :param repo_url: 源码仓库地址
        """
        git_project = GitProject.parse_from_repo_url(repo_url, "tc_git")
        _id = quote(git_project.path_with_namespace, safe="")
        _url = f"api/v3/projects/{_id}"
        resp = self._session.delete(urljoin(self._api_url, _url))
        validate_response(resp)

    def initial_repo(self, repo_url: str, template: Template, context: dict):
        """初始化插件代码

        :param repo_url: 源码仓库地址
        :param source_init_template: 初始化模板名称
        :param context: 渲染源码仓库的上下文
        """
        git_project = GitProject.parse_from_repo_url(repo_url, "tc_git")
        commit_message = "init repo"

        with generate_temp_dir() as dest_dir:
            # 克隆仓库到工作目录 dest_dir
            self._client.clone(self._build_repo_url_with_auth(git_project), dest_dir)
            # 将模板代码渲染到 dest_dir
            self._render_template_to_dest_dir(template, dest_dir, context)

            # 配置 Git 用户信息
            self._fix_git_user_config(dest_dir / ".git" / "config")

            # 提交并推送代码
            self._client.add(dest_dir, Path("."))
            self._client.commit(dest_dir, message=commit_message)
            self._client.push(dest_dir)

    def add_member(self, repo_url: str, username: str, role: TencentGitMemberRole):
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

    def _get_user_id(self, username: str) -> int:
        """根据用户名获取 user_id"""
        _url = f"api/v3/users/{username}"
        resp = self._session.get(urljoin(self._api_url, _url))
        return validate_response(resp).json()["id"]

    def _get_namespace_id(self) -> int:
        """获取 groups 的命名空间 id"""
        _url = f"api/v3/groups/{quote(self._namespace, safe='')}"
        resp = self._session.get(urljoin(self._api_url, _url))
        validate_response(resp)
        return resp.json()["id"]

    def _download_to(self, repo_url: str, source_dir: Path, dest_dir: Path):
        """将代码仓库指定目录的内容下载到本地 `dest_dir` 目录"""
        git_project = GitProject.parse_from_repo_url(repo_url, "tc_git")
        repository = self._build_repo_url_with_auth(git_project)
        with generate_temp_dir() as temp_dir:
            real_source_dir = temp_dir / source_dir
            self._client.clone(repository, path=temp_dir, depth=1)
            self._client.clean_meta_info(temp_dir)
            for path in real_source_dir.iterdir():
                shutil.move(str(path), str(dest_dir / path.relative_to(real_source_dir)))
        return dest_dir

    def _render_template_to_dest_dir(self, template: Template, dest_dir: Path, context: dict):
        """渲染模板到目标目录"""

        if template.type == TemplateType.NORMAL:
            # 普通代码仓库，用模板引擎渲染
            templater = Templater(tmpl_name=template.name, type=TemplateType.NORMAL, **context)
            templater.write_to_dir(dest_dir)
        elif template.type == TemplateType.PLUGIN:
            # 插件模板用 cookiecutter 渲染
            with generate_temp_dir() as temp_dir, generate_temp_dir() as render_dir:
                self._download_to(template.repo_url, template.get_source_dir(), temp_dir)
                cookiecutter(str(temp_dir), no_input=True, extra_context=context, output_dir=str(render_dir))
                items = list(render_dir.iterdir())
                if len(items) == 1:
                    # 对于自带根目录的模板, 需要丢弃最外层
                    items = list(items[0].iterdir())
                for item in items:
                    shutil.move(str(item), str(dest_dir / item.name))
        else:
            raise NotImplementedError


def create_new_repo_and_initialized(module: Module, repo_type: str, operator: str):
    """新建代码仓库并初始化

    :param repo_type: sourcectl type name, see SourceTypeSpecConfig table data for all names
    """
    conf = settings.APP_REPO_CONF
    user_credentials = {"private_token": conf["private_token"]}
    initializer_cls = get_sourcectl_type(repo_type).initializer_class
    if not initializer_cls:
        raise NotImplementedError

    try:
        template = Template.objects.get(name=module.source_init_template)
    except Template.DoesNotExist:
        raise ValueError(f"Template {module.source_init_template} does not exist")

    initializer = initializer_cls(
        repository_group=settings.APP_REPOSITORY_GROUP, api_url=conf["api_url"], user_credentials=user_credentials
    )
    # 创建代码仓库，仓库名为应用 ID_模块名，仓库可见级别为公开
    repo_name = f"{module.application.code}_{module.name}"
    description = f"{module.application.name}({module.name} 模块)"
    repo_project = initializer.create_project(repo_name, TencentGitVisibleLevel.PUBLIC, description)

    # 绑定源码仓库信息到模块
    connector = get_repo_connector(repo_type, module)
    connector.bind(repo_project.repo_url, repo_auth_info={})

    try:
        # 初始化代码仓库
        context = get_module_init_repo_context(module, template.type)
        initializer.initial_repo(repo_project.repo_url, template, context)

        # 将当前操作者添加为仓库的 Master
        initializer.add_member(repo_project.repo_url, operator, TencentGitMemberRole.MASTER)
    except Exception:
        # 任何异常发生时回滚已创建的仓库
        logger.exception(f"Failed to initialize repository, delete repository({repo_name})...")
        try:
            initializer.delete_project(repo_project.repo_url)
        except Exception:
            logger.exception(f"Failed to delete repository({repo_name}) during rollback")
        raise
