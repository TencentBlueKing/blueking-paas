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

"""Repo connectors for applications"""

import abc
import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import dedent
from typing import Any, Dict, Optional, Type
from urllib.parse import quote, urljoin

from cookiecutter.main import cookiecutter
from django.conf import settings
from django.db.models import Model

from paasng.infras.oauth2.utils import get_oauth2_client_secret
from paasng.platform.applications.models import Application
from paasng.platform.modules.models import Module
from paasng.platform.sourcectl.git.client import GitClient, MutableURL
from paasng.platform.sourcectl.models import (
    GitProject,
    GitRepository,
    RepoBasicAuthHolder,
    RepositoryInstance,
    SvnRepository,
)
from paasng.platform.sourcectl.source_types import get_sourcectl_type, get_sourcectl_types
from paasng.platform.sourcectl.svn.admin import get_svn_authorization_manager, promote_repo_privilege_temporary
from paasng.platform.sourcectl.svn.client import SvnRepositoryClient, acquire_repo
from paasng.platform.sourcectl.svn.exceptions import CannotInitNonEmptyTrunk
from paasng.platform.sourcectl.svn.server_config import get_bksvn_config
from paasng.platform.sourcectl.utils import compress_directory, generate_temp_dir, generate_temp_file
from paasng.platform.templates.constants import TemplateType
from paasng.platform.templates.models import Template
from paasng.platform.templates.templater import Templater
from paasng.utils.basic import get_username_by_bkpaas_user_id, unique_id_generator
from paasng.utils.blobstore import BlobStore, make_blob_store

logger = logging.getLogger(__name__)


@dataclass
class SourceSyncResult:
    """The result of one templated source sync procedure"""

    dest_type: str
    error: str = ""
    extra_info: Dict = field(default_factory=dict)

    def is_success(self):
        return not self.error


class ModuleRepoConnector(abc.ABC):
    """A ModuleRepoConnector connects application with VCS repositories"""

    auth_method: str

    def __init__(self, module: Module, repo_type: str):
        self.module = module
        self.application = self.module.application
        self.repo_type = repo_type

    @abc.abstractmethod
    def bind(self, repo_url: Optional[str] = "", source_dir: str = "", **kwargs) -> RepositoryInstance:
        """Bind a repo address to current module"""

    @abc.abstractmethod
    def sync_templated_sources(self, context: dict) -> SourceSyncResult:
        """Sync the templated source to remote object storage
        NOTE: Only supports normal templates, that is, the template code is stored in blob_url
        """

    @abc.abstractmethod
    def init_repo(self, template: Template, repo_url: str, context: dict):
        """
        Initialize the template code into the source code repository of the application.

        For normal templates, download the template code from object storage.
        For plugin templates, download the template code from the code repository.
        and render the app  context into the template code based on the template's `render_method`.
        """


class DBBasedMixin:
    """Repo connector, which provides some utilities to set/get repo object, stores
    data in database.
    """

    @property
    def repository_model(self) -> Type[Model]:
        raise NotImplementedError

    # For type checking
    application: Application
    module: Module
    repo_type: str

    def _get_or_create_repo_obj(self, repo_url: str, source_dir: str) -> Any:
        """Get or create a repository object by given url and source_dir."""
        repo_kwargs = {
            "server_name": self.repo_type,
            "repo_url": repo_url,
            "source_dir": source_dir,
            "tenant_id": self.application.tenant_id,
        }
        # Not using `get_or_create` because it might return more than 1 results
        repo_objs = self.repository_model.objects.filter(**repo_kwargs)[:1]
        if repo_objs:
            return repo_objs[0]

        # `owner` field does not have anything to do with "ownership", it only mean "the user who use this
        # repo_url for the first time"
        return self.repository_model.objects.create(owner=self.application.owner, **repo_kwargs)

    def save_repo_info(self, repo_url, source_dir: str = "") -> RepositoryInstance:
        repo = self._get_or_create_repo_obj(repo_url, source_dir=source_dir)
        self.module.source_type = self.repo_type
        self.module.source_repo_id = repo.id
        self.module.save(update_fields=["source_type", "source_repo_id"])
        return repo

    def untie_repo(self):
        """Unbind the module and repo"""
        self.module.source_type = None
        self.module.source_repo_id = None
        self.module.save(update_fields=["source_type", "source_repo_id"])

    def get_repo(self):
        return self.module.get_source_obj()


class IntegratedSvnAppRepoConnector(ModuleRepoConnector, DBBasedMixin):
    """RepoBinder for integrated svn repository, features:

    - Auto create and manage module's repo auth through a customized http service
    - Auto fill up app source directory with generated template because we have the admin
      credentials and committing to svn is also less fragile cause svn is centralized
    """

    auth_method = "internal"
    repository_model = SvnRepository

    def __init__(self, module: Module, repo_type: str):
        super().__init__(module, repo_type)
        self.auth_manager = get_svn_authorization_manager(self.application)

    def _initial_application_root(self, desired_root):
        """初始化应用根目录"""
        # 首先初始化权限
        self.auth_manager.initialize(desired_root)

        # 创建目录
        base_info = get_sourcectl_type(self.repo_type).config_as_arguments()
        try:
            self.auth_manager.set_paas_user_root_privilege(path=desired_root, write=True, read=True)
            return self._acquire_repo(
                desired_name=desired_root,
                base_info=base_info,
                with_branches_and_tags=False,
            )
        finally:
            self.auth_manager.set_paas_user_root_privilege(path=desired_root, write=False, read=True)

    def _acquire_module_repo(self, desired_root):
        """创建 module 相关 repo"""
        # 创建目录
        try:
            self.auth_manager.set_paas_user_root_privilege(path=desired_root, write=True, read=True)
            server_config = get_bksvn_config(name=self.repo_type)
            return self._acquire_repo(
                desired_name=unique_id_generator(self.module.name),
                base_info=server_config.as_module_arguments(root_path=desired_root),
                with_branches_and_tags=True,
            )
        finally:
            self.auth_manager.set_paas_user_root_privilege(path=desired_root, write=False, read=True)

    @staticmethod
    def _acquire_repo(desired_name, base_info, with_branches_and_tags=True) -> str:
        """Auto generated a repo address"""
        repo_info = acquire_repo(desired_name=desired_name, with_branches_and_tags=with_branches_and_tags, **base_info)
        return repo_info["repo_url"]

    def bind(self, repo_url: Optional[str] = "", source_dir: str = "", **kwargs):
        if not repo_url:
            # get unique repo root, sample-app will get sample-app-7Gt
            unique_app_root = unique_id_generator(self.application.code)
            # initialize application's repo as parent
            self._initial_application_root(desired_root=unique_app_root)
            repo_url = self._acquire_module_repo(desired_root=unique_app_root)

        return self.save_repo_info(repo_url, source_dir=source_dir)

    def sync_templated_sources(self, context) -> SourceSyncResult:
        """Sync the templated source to remote object storage
        NOTE: Only supports normal templates, that is, the template code is stored in blob_url
        """
        return generate_downloadable_app_template(self.module, context)

    def init_repo(self, template: Template, repo_url: str, context: dict):
        """Sync the source to svn server with an initial commit"""
        with generate_temp_dir() as source_path, promote_repo_privilege_temporary(self.application):
            # SVN 仅支持普通模板，并只能从 blob_url（模板上传到对象存储的路径）下载模板
            try:
                templater = Templater(tmpl_name=self.module.source_init_template, type=TemplateType.NORMAL, **context)
                templater.write_to_dir(source_path)
            except Exception:
                logger.exception("unable to render app source template %s", self.module.source_init_template)
                raise

            svn_credentials = get_bksvn_config(name=self.repo_type).get_admin_credentials()
            sync_procedure = SvnSyncProcedure(repo_url, svn_credentials["username"], svn_credentials["password"])
            return sync_procedure.run(source_path=str(source_path))


class ExternalGitAppRepoConnector(ModuleRepoConnector, DBBasedMixin):
    """RepoBinder for external git repository, features:

    - Only save the bind relation in models without auto create repo
    - Upload the generated source template to S3 instead of modifying the original repo
    """

    auth_method = "oauth"
    repository_model = GitRepository
    client = GitClient()

    def bind(self, repo_url: Optional[str] = "", source_dir: str = "", **kwargs):
        if not repo_url:
            raise ValueError('must provide "repo_url" when connecting to git')
        return self.save_repo_info(repo_url, source_dir=source_dir)

    def sync_templated_sources(self, context) -> SourceSyncResult:
        """Sync the templated source to remote object storage
        NOTE: Only supports normal templates, that is, the template code is stored in blob_url
        """
        return generate_downloadable_app_template(self.module, context)

    def init_repo(self, template: Template, repo_url: str, context: dict):
        """
        Initialize the template code into the source code repository of the application.

        :param template: Template object
        :param repo_url: Repo URL
        """
        git_project = GitProject.parse_from_repo_url(repo_url, self.module.source_type)
        commit_message = "init repo"

        with generate_temp_dir() as dest_dir:
            # 克隆仓库到工作目录 dest_dir
            self.client.clone(self._build_repo_url_with_auth(git_project), dest_dir)
            # 将模板代码渲染到 dest_dir
            self._render_template_to_dest_dir(template, dest_dir, context)

            # 配置 Git 用户信息
            self._fix_git_user_config(dest_dir / ".git" / "config")

            # 提交并推送代码
            self.client.add(dest_dir, Path("."))
            self.client.commit(dest_dir, message=commit_message)
            self.client.push(dest_dir)

    def _render_template_to_dest_dir(self, template: Template, dest_dir: Path, context: dict):
        """渲染模板到目标目录
        NOTE: 普通模板从对象存储中下载模板代码，插件应用从代码仓库中下载模板代码。并根据模板的的 render_method 将应用相关的 context 渲染到模板代码中
        """

        if template.type == TemplateType.NORMAL:
            # 普通代码仓库，用 djagno 模板引擎渲染
            templater = Templater(tmpl_name=template.name, type=TemplateType.NORMAL, **context)
            templater.write_to_dir(dest_dir)
        elif template.type == TemplateType.PLUGIN:
            with generate_temp_dir() as temp_dir, generate_temp_dir() as render_dir:
                # 从代码仓库下载代码到本地目录
                self._download_to(template.repo_url, template.get_source_dir(), temp_dir)
                # 插件模板用 cookiecutter 渲染
                cookiecutter(str(temp_dir), no_input=True, extra_context=context, output_dir=str(render_dir))
                items = list(render_dir.iterdir())
                if len(items) == 1:
                    # 对于自带根目录的模板, 需要丢弃最外层
                    items = list(items[0].iterdir())
                for item in items:
                    shutil.move(str(item), str(dest_dir / item.name))
        else:
            raise NotImplementedError

    def _download_to(self, repo_url: str, source_dir: Path, dest_dir: Path):
        """将代码仓库指定目录的内容下载到本地 `dest_dir` 目录"""
        # FIXME: 模板代码仓库的托管类型，后续扩展到工蜂以外的代码仓库再在 Template model 中添加 repo_type 字段
        repo_type = "tc_git"
        git_project = GitProject.parse_from_repo_url(repo_url, repo_type)
        repository = self._build_repo_url_with_auth(git_project)

        with generate_temp_dir() as temp_dir:
            real_source_dir = temp_dir / source_dir
            self.client.clone(repository, path=temp_dir, depth=1)
            self.client.clean_meta_info(temp_dir)
            for path in real_source_dir.iterdir():
                shutil.move(str(path), str(dest_dir / path.relative_to(real_source_dir)))
        return dest_dir

    def _build_repo_url_with_auth(self, project: GitProject) -> MutableURL:
        """构建包含 username:token 的代码仓库地址

        NOTE: 用于拉取模板代码和将代码写入到平台创建的代码仓库中。这里不能使用用户的 Oauth Token，只能用平台的 Private Token
        """

        username = "private"
        password = settings.APP_REPO_CONF["private_token"]
        api_url = settings.APP_REPO_CONF["api_url"]

        return MutableURL(urljoin(api_url, project.path_with_namespace)).replace(
            username=quote(username), password=quote(password)
        )

    def _fix_git_user_config(self, dest_dir: Path):
        """修复 git 的用户信息缺失问题"""
        with dest_dir.open(mode="a") as fh:
            fh.write(
                dedent(
                    f"""
            [user]
                email = {settings.APP_REPO_CONF["email"]}
                name = {settings.APP_REPO_CONF["username"]}
            """
                )
            )


class ExternalBasicAuthRepoConnector(ModuleRepoConnector, DBBasedMixin):
    """RepoBinder for external basic auth repository(including bare_git & bare_svn), features:

    - Only save the bind relation in models without auto create repo
    - Save basic auth along with repo
    - Upload the generated source template to S3 instead of modifying the original repo
    """

    auth_method = "basic"

    @property
    def repository_model(self) -> Type[Model]:
        types = get_sourcectl_types()
        if types.names.validate_git(self.repo_type):
            return GitRepository
        elif types.names.validate_svn(self.repo_type):
            return SvnRepository
        raise NotImplementedError("Unsupported VCS type")

    def update_repo_basic_auth(self, repo_obj: RepositoryInstance, repo_auth_info) -> RepoBasicAuthHolder:
        """Update basic auth of bind repo"""
        holder, created = RepoBasicAuthHolder.objects.update_or_create(
            repo_id=repo_obj.get_identity(),
            repo_type=repo_obj.get_source_type(),
            module=self.module,
            defaults={
                "username": repo_auth_info.get("username", ""),
                "password": repo_auth_info.get("password", ""),
                "tenant_id": self.module.tenant_id,
            },
        )
        if created:
            logger.debug("Creating basic auth of repo<%s>", repo_obj.get_repo_url())

        return holder

    def bind(self, repo_url: Optional[str] = "", source_dir: str = "", **kwargs):
        """绑定仓库同时，为仓库绑定 Basic Auth"""
        if not repo_url:
            raise ValueError('must provide "repo_url" when connecting to git')

        repo_obj = self.save_repo_info(repo_url, source_dir=source_dir)
        repo_auth_info = kwargs["repo_auth_info"]
        self.update_repo_basic_auth(repo_obj, repo_auth_info)
        return repo_obj

    def sync_templated_sources(self, context) -> SourceSyncResult:
        """Sync the templated source to remote object storage
        NOTE: Only supports normal templates, that is, the template code is stored in blob_url
        """
        return generate_downloadable_app_template(self.module, context)


@dataclass
class SvnSyncProcedure:
    """Sync templated sources to SVN repo with a commit"""

    repo_url: str
    username: str
    password: str

    def run(self, source_path: str, sub_path: str = "trunk"):
        client = SvnRepositoryClient(self.repo_url, self.username, self.password)
        try:
            client.sync_dir(local_path=source_path, remote_path=sub_path)
        except CannotInitNonEmptyTrunk as e:
            return SourceSyncResult(dest_type="svn", error="already synced: {}".format(e))
        else:
            return SourceSyncResult(
                dest_type="svn", extra_info={"remote_source_root": urljoin(self.repo_url, "trunk")}
            )


@dataclass
class BlobStoreSyncProcedure:
    """Sync templated source to Blob Store."""

    blob_store: BlobStore
    key: str

    downloadable_address_expires_in = 3600 * 4

    def run(self, source_path: str) -> SourceSyncResult:
        """Compress the source_path and upload the content to given key"""
        with generate_temp_file(suffix=".tar.gz") as package_path:
            logger.debug("compressing templated source, key=%s...", self.key)
            compress_directory(source_path, package_path)
            self.blob_store.upload_file(package_path, self.key, ExtraArgs={"ACL": "private"})

        # Generate a temporary accessible url for source codes
        url = self.blob_store.generate_presigned_url(key=self.key, expires_in=self.downloadable_address_expires_in)
        return SourceSyncResult(
            dest_type=self.blob_store.STORE_TYPE,
            extra_info={
                "downloadable_address": url,
                "downloadable_address_expires_in": self.downloadable_address_expires_in,
            },
        )


def get_repo_connector(repo_type: str, module: Module) -> ModuleRepoConnector:
    """Get a connector object by given repository type

    :param repo_type: type of repository
    :param module: a Module object
    """
    from paasng.platform.sourcectl.source_types import get_sourcectl_type

    type_ = get_sourcectl_type(repo_type).connector_class
    return type_(module, repo_type)


def generate_downloadable_app_template(module: Module, context: Optional[Dict[str, Any]] = None) -> SourceSyncResult:
    """Generate a downloadable URL for templated app source code

    :param context: Context for rendering the source code
    """
    application = module.application
    if context is None:
        # generate default context
        client_secret = get_oauth2_client_secret(application.code)
        context = {
            "region": application.region,
            "owner_username": get_username_by_bkpaas_user_id(application.owner),
            "app_code": application.code,
            "app_secret": client_secret,
            "app_name": application.name,
        }
    key = f"app-template-instances/{application.region}/{application.code}-{module.name}.tar.gz"
    sync_procedure = BlobStoreSyncProcedure(
        blob_store=make_blob_store(bucket=settings.BLOBSTORE_BUCKET_APP_SOURCE), key=key
    )
    with generate_temp_dir() as source_path:
        try:
            templater = Templater(tmpl_name=module.source_init_template, type=TemplateType.NORMAL, **context)
            templater.write_to_dir(source_path)
        except Exception:
            logger.exception("unable to render app source template %s", module.source_init_template)
            raise
        return sync_procedure.run(str(source_path))
