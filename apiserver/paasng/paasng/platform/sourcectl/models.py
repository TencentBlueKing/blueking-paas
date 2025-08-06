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

import datetime
import logging
import re
from collections import namedtuple
from dataclasses import dataclass, field
from typing import Dict, Generic, List, Optional, Tuple, TypeVar
from urllib.parse import urlparse

from bkpaas_auth.models import User
from blue_krill.models.fields import EncryptField
from django.db import models
from django.utils.translation import gettext_lazy as _
from jsonfield import JSONField
from translated_fields import TranslatedFieldWithFallback
from typing_extensions import Protocol

from paasng.core.tenant.fields import tenant_id_field_factory
from paasng.platform.modules.models import Module
from paasng.platform.sourcectl.exceptions import PackageAlreadyExists
from paasng.platform.sourcectl.source_types import get_sourcectl_type
from paasng.platform.sourcectl.svn.admin import get_svn_authorization_manager_cls
from paasng.platform.sourcectl.svn.server_config import get_bksvn_config
from paasng.utils.models import AuditedModel, BkUserField, OwnerTimestampedModel, TimestampedModel
from paasng.utils.text import remove_prefix, remove_suffix

logger = logging.getLogger(__name__)


class RepositoryInstance(Protocol):
    """A interface for Repository Obj"""

    def get_identity(self) -> int:
        """返回 RepositoryInstance 的唯一标识"""

    def get_source_type(self) -> str:
        """返回源码库的类型"""

    def get_source_dir(self) -> str:
        """返回源码目录"""

    def get_display_name(self) -> str:
        """返回源码库的展示用名字"""

    def get_repo_url(self) -> Optional[str]:
        """[Optional] 返回仓库地址"""

    def get_repo_fullname(self) -> Optional[str]:
        """[Optional] 返回当前源码库的全称"""


class RepositoryMixin:
    pk: int
    server_name: str
    repo_url: str
    source_dir: str

    @property
    def display_name(self):
        return get_sourcectl_type(self.server_name).label

    def get_identity(self) -> int:
        """返回 RepositoryInstance 的唯一标识"""
        return self.pk

    def get_source_type(self) -> str:
        """返回源码库的类型"""
        return self.server_name or ""

    def get_source_dir(self) -> str:
        """返回源码目录"""
        return self.source_dir or ""

    def get_display_name(self) -> str:
        """返回源码库的展示用名字"""
        return self.display_name

    def get_repo_url(self) -> Optional[str]:
        """[Optional] 返回仓库地址"""
        return self.repo_url

    def get_repo_fullname(self) -> Optional[str]:
        """[Optional] 返回当前源码库的全称"""
        return self.repo_url


class SvnRepository(OwnerTimestampedModel, RepositoryMixin):
    """基于 Svn 的软件存储库"""

    server_name = models.CharField(verbose_name="SVN 服务名称", max_length=32)
    repo_url = models.CharField(verbose_name="项目地址", max_length=2048)
    source_dir = models.CharField(verbose_name="源码目录", max_length=2048, null=True)
    tenant_id = tenant_id_field_factory()

    def get_repo_fullname(self) -> str:
        """返回当前源码库的全称

        >>> SvnRepository(repo_url="svn://svn.example.com:8080/v3apps/demo").get_repo_fullname()
        "v3apps/demo"
        """
        return urlparse(self.repo_url).path

    def get_repo_url(self) -> Optional[str]:
        from paasng.platform.sourcectl.type_specs import BkSvnSourceTypeSpec

        if isinstance(get_sourcectl_type(self.server_name), BkSvnSourceTypeSpec):
            parse_result = urlparse(self.repo_url)
            if parse_result.scheme == "http" and get_bksvn_config(name=self.server_name).need_security:
                return "https://" + parse_result.netloc + parse_result.path
            return self.repo_url
        else:
            # for bare_svn
            return self.repo_url

    def get_trunk_url(self):
        """[deprecated] 返回仓库地址

        目前前端对于 git 项目, 仍然使用 trunk_url, 这里应该调整为使用 repo_url
        """
        repo_url = self.get_repo_url()
        assert repo_url
        return remove_suffix(repo_url, "/") + "/trunk"


class SvnAccountManager(models.Manager):
    @staticmethod
    def generate_account_by_user(username):
        return username

    def reset_account(self, instance, user):
        if instance.user != user.pk:
            raise ValueError(user.pk)

        svn_auth_manager_cls = get_svn_authorization_manager_cls()
        data = svn_auth_manager_cls.create_svn_client().reset_user(
            account=user.username,
        )
        instance.account = user.username
        instance.save()  # update updated field
        return {
            "password": data["password"],
            "user": user.username,
            "account": instance.account,
            "id": instance.id,
        }


class SvnAccount(TimestampedModel):
    """svn account for developer

    [multi-tenancy] This model is not tenant-aware. Should add tenant_id field if
    it's more convenient to get tenant_id from user.

    NOTE: 平台 bk_svn 仓库(非 bare_svn)的支持逐步废弃, 因此不需要再支持多租户功能
    """

    account = models.CharField(max_length=64, help_text="目前仅支持固定格式", unique=True)
    user = BkUserField()
    synced_from_paas20 = models.BooleanField(default=False, help_text="账户信息是否从 PaaS 2.0 同步过来")

    objects = SvnAccountManager()

    class Meta:
        pass


class GitRepository(OwnerTimestampedModel, RepositoryMixin):
    """基于 Git 的软件存储库"""

    server_name = models.CharField(verbose_name="GIT 服务名称", max_length=32)
    repo_url = models.CharField(verbose_name="项目地址", max_length=2048)
    source_dir = models.CharField(verbose_name="源码目录", max_length=2048, null=True)
    tenant_id = tenant_id_field_factory()

    def get_repo_fullname(self) -> str:
        try:
            return self._get_alias_name()
        except ValueError:
            logger.exception("failed to parse %s for getting alias name", self.repo_url)
            return self.repo_url

    def _get_alias_name(self) -> str:
        """获取仓库别名 namespace/repo_name 目前主要给蓝盾使用"""
        parse_result = urlparse(self.repo_url)
        repo_regex = re.compile(r"^/(?P<alias_name>.+?)(?:\.git)?$")
        obj = re.search(repo_regex, parse_result.path)
        if obj:
            return obj.group("alias_name")
        raise ValueError("no alias name found")


class DockerRepository(OwnerTimestampedModel, RepositoryMixin):
    """容器镜像仓库"""

    server_name = models.CharField(verbose_name="DockerRegistry 服务名称", max_length=32)
    repo_url = models.CharField(
        verbose_name="项目地址",
        max_length=2048,
        help_text="形如 registry.hub.docker.com/library/python, 也可省略 registry 地址",
    )
    source_dir = models.CharField(verbose_name="源码目录", max_length=2048, null=True)
    tenant_id = tenant_id_field_factory()

    @property
    def display_name(self):
        return _("容器镜像仓库")

    def get_repo_fullname(self) -> str:
        """Get the image name

        Example:
        >>> DockerRepository(repo_url="python").get_repo_fullname()
        "python"
        >>> DockerRepository(repo_url="library/python").get_repo_fullname()
        "library/python"
        >>> DockerRepository(repo_url="docker.io/library/python").get_repo_fullname()
        "library/python"
        >>> DockerRepository(repo_url="registry.hub.docker.com/library/python").get_repo_fullname()
        "library/python"
        """
        parts = self.repo_url.split("/")
        if len(parts) <= 2:
            # short name
            return self.repo_url
        else:
            # full name, trim the repository name
            return "/".join(parts[1:])


class SourcePackageRepository:
    def __init__(self, module: "Module"):
        self.module = module

    def get_identity(self) -> int:
        """返回 RepositoryInstance 的唯一标识, SourcePackageRepository 不支持"""
        raise NotImplementedError

    def get_source_type(self) -> str:
        return self.module.source_type or ""

    def get_source_dir(self) -> str:
        return ""

    def get_repo_url(self) -> Optional[str]:
        return None

    def get_repo_fullname(self) -> Optional[str]:
        return None

    def get_display_name(self) -> str:
        return self.get_source_type()


class SourcePackageManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().exclude(is_deleted=True)

    def store(self, module: "Module", policy: "SPStoragePolicy", operator: Optional[User] = None):
        """根据存储策略, 将 package 的配置记录到数据库中"""
        qs = self.filter(module=module)
        if qs.filter(version=policy.stat.version).exists() and not policy.allow_overwrite:
            raise PackageAlreadyExists(f"A source package of the same version[{policy.stat.version}] already exists.")

        package, _ = self.update_or_create(
            defaults=dict(
                package_name=policy.stat.name,
                package_size=policy.stat.size,
                sha256_signature=policy.stat.sha256_signature,
                meta_info=policy.stat.meta_info,
                relative_path=policy.stat.relative_path,
                storage_engine=policy.engine,
                storage_path=policy.path,
                storage_url=policy.url,
                owner=getattr(operator, "pk", None),
                tenant_id=module.tenant_id,
            ),
            module=module,
            version=policy.stat.version,
        )
        return package


class SourcePackage(OwnerTimestampedModel):
    """源码包存储信息"""

    module = models.ForeignKey(
        "modules.Module", on_delete=models.CASCADE, related_name="packages", db_constraint=False
    )
    version = models.CharField(verbose_name="版本号", max_length=128)
    package_name = models.CharField(verbose_name="源码包原始文件名", max_length=128)
    package_size = models.BigIntegerField(verbose_name="源码包大小, bytes")
    storage_engine = models.CharField(verbose_name="存储引擎", max_length=64, help_text="源码包真实存放的存储服务类型")
    storage_path = models.CharField(
        verbose_name="存储路径", max_length=1024, help_text="[deprecated] 源码包在存储服务中存放的位置"
    )
    storage_url = models.CharField(verbose_name="存储地址", max_length=1024, help_text="可获取到源码包的 URL 地址")

    meta_info = JSONField(null=True, help_text="源码包的元信息, 例如 S-Mart 应用的 app.yaml")
    sha256_signature = models.CharField(verbose_name="sha256数字签名", max_length=64, null=True)
    relative_path = models.CharField(
        max_length=255,
        verbose_name="源码入口的相对路径",
        help_text="如果压缩时将目录也打包进来, 入目录名是 foo, 那么 relative_path = 'foo/'",
    )
    is_deleted = models.BooleanField(
        default=False,
        verbose_name="源码包是否已被清理",
        help_text="如果 SourcePackage 指向的源码包已被清理, 则设置该值为 True",
    )
    tenant_id = tenant_id_field_factory()

    objects = SourcePackageManager()
    default_objects = models.Manager()

    class Meta:
        unique_together = ("module", "version")


@dataclass
class SPStat:
    """SourcePackage stats.

    :param name: The package file name, e.g. 'foo-1.0.0.tar.gz'.
    :param version: The version number parsed from the package, e.g. '1.0.0'.
    """

    name: str
    version: str
    size: int
    meta_info: Dict
    sha256_signature: str
    relative_path: str = "./"


@dataclass
class SPStoragePolicy:
    """源码包存储策略"""

    path: str
    url: str

    stat: SPStat
    allow_overwrite: bool = False
    engine: str = "GenericRemoteClient"


@dataclass
class Repository:
    """Git 的仓库模型"""

    namespace: str
    project: str
    description: str
    avatar_url: str
    web_url: str
    http_url_to_repo: str
    ssh_url_to_repo: str
    created_at: datetime.datetime
    last_activity_at: datetime.datetime

    @property
    def fullname(self):
        return f"{self.namespace} / {self.project}"


@dataclass
class GitGroup:
    """Git 的组模型"""

    name: str
    path: str
    description: str
    avatar_url: str
    web_url: str


@dataclass
class AlternativeVersion:
    name: str
    type: str
    revision: str
    url: str
    last_update: Optional[datetime.datetime] = None
    message: str = ""
    extra: dict = field(default_factory=dict)


@dataclass
class CommitLog:
    message: str = ""
    revision: str = ""
    date: datetime.datetime = field(default_factory=datetime.datetime.now)
    author: str = ""
    changelist: List[Tuple[str, str]] = field(default_factory=list)


class DiffChange(tuple):
    @classmethod
    def format_from_gitlab(cls, diff):
        flag = "M"
        content = diff["new_path"]
        if diff["new_file"]:
            flag = "A"
        elif diff["deleted_file"]:
            flag = "D"
        elif diff["renamed_file"]:
            flag = "R"
            content = f"{diff['old_path']} -> {diff['new_path']}"
        return cls((flag, content))


@dataclass
class VersionInfo:
    """VersionInfo 是对代码版本的一种通用抽象

    对于 SVN 仓库而言:
        revision 是当前的 commit id(自增的 int 数字)
        version_name 是 humanized 的名称
        version_type 是 Literal[branch, trunk]

        样例数据: VersionInfo(revision="10086", version_name="v1", version_type="branch")

    对于 Git 仓库而言:
        revision 是当前的 commit id(hash)
        version_name 是 branch/tag 的名称, 例如 main, master 等
        version_type 是 Literal[branch, tag]

        样例数据: VersionInfo(revision="1304382d8c60220869624cc6b", version_name="main", version_type="branch")

    对于源码包仓库而言(lesscode应用和S-Mart应用):
        revision 是当前包的 semver
        version_name 是包的全名
        version_type 是 Literal[package]

        样例数据: VersionInfo(revision="2.2.1", version_name="2.2.1", version_type="package")

    对于采用了镜像模式的 S-Mart 应用:
        revision 是当前包的 semver
        version_name 是镜像的 tag
        version_type 是 Literal[tag]

        样例数据: VersionInfo(revision="2.2.1", version_name="2.2.1", version_type="tag")

    对于云原生镜像而言:
        revision 为空串
        version_name 是镜像的 tag
        version_type 是 Literal[tag]

        样例数据: VersionInfo(revision="", version_name="v1", version_type="tag")

    对于云原生应用选择已构建的镜像部署时(模块本身非镜像):
        revision 当前的 sha256 digest
        version_name 是镜像的 tag
        version_type 是 Literal[image]

        样例数据:
        VersionInfo(revision="sha256:a2c6683598be55e2ddd7be53acd820b68cf8db95f84e38cd511f0683feb114a8",
        version_name="master-2404091749", version_type="image")
        返回给前端时, 会进行源码构建追溯成:
        VersionInfo(revision="1304382d8c60220869624cc6b", version_name="master", version_type="branch")

    对于镜像仓库而言(旧的镜像应用)
        revision 是镜像的 tag *注: 这里没有实现成 存储镜像hash 是因为暂时没有地方用到*
        version_name 是镜像的 tag
        version_type 是 Literal[tag]

        样例数据: VersionInfo(revision="2.2.1", version_name="2.2.1", version_type="tag")
    """

    # TODO 在 VersionInfo 构建阶段增加值校验, 同时增加 source_origin 表示来源类型 ?
    revision: str
    version_name: str
    version_type: str


T = TypeVar("T")


@dataclass
class GenericPage(Generic[T]):
    items: List[T]
    total_page: int
    cur_page: int
    per_page: int

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)


@dataclass
class GitProject:
    """
    Git项目
    """

    name: str
    # 用户名和组名(包括 sub_group) 等前缀路径, 即命名空间
    namespace: str
    # 源码控制系统名称 "name" of sourcectl type
    type: str

    @classmethod
    def parse_from_repo_url(cls, repo_url: str, sourcectl_type: str) -> "GitProject":
        """从 repo_url 中解析出 GitProject

        :param repo_url: 仓库地址
        :param sourcectl_type: 源码控制系统名称

        example:
        -   http://domain/{group_name}/{project_name}.git
        -   http://domain/{user_name}/{project_name}.git
        -   http://domain/{group_name}/{project_name}
        -   http://domain/{user_name}/{project_name}
        -   http://domain/groups/{group_name}/{project_name}
        """
        parsing_repo_url = remove_suffix(repo_url, ".git")
        parsed_result = urlparse(parsing_repo_url)
        path_with_namespace = remove_prefix(parsed_result.path, "/")
        # 去除可能的'groups/'前缀（如果存在）
        path_with_namespace = remove_prefix(path_with_namespace, "groups/")

        return cls.parse_from_path_with_namespace(
            path_with_namespace=path_with_namespace, sourcectl_type=sourcectl_type
        )

    @classmethod
    def parse_from_path_with_namespace(cls, path_with_namespace: str, sourcectl_type: str) -> "GitProject":
        """从 path_with_namespace 解析出 GitProject
        由于 path_with_namespace 未记载源码控制系统类型, 因此需在参数中指定。

        :param path_with_namespace:
        :param sourcectl_type: 源码控制系统名称
        """
        namespace, name = path_with_namespace.rsplit("/", 1)
        return cls(name=name, namespace=namespace, type=sourcectl_type)

    @property
    def path_with_namespace(self):
        return f"{self.namespace}/{self.name}"


@dataclass
class ChangedFile:
    """被修改的文件详情"""

    path: str
    content: str


@dataclass
class CommitInfo:
    """提交数据"""

    branch: str
    message: str
    add_files: List[ChangedFile] = field(default_factory=list)
    edit_files: List[ChangedFile] = field(default_factory=list)
    delete_files: List[ChangedFile] = field(default_factory=list)


class BasicAuthHolderManager(models.Manager):
    def exists_by_repo(self, module: "Module", repo_obj: RepositoryInstance) -> bool:
        return bool(self.filter(repo_id=repo_obj.get_identity(), repo_type=repo_obj.get_source_type(), module=module))

    def get_by_repo(self, module: "Module", repo_obj: RepositoryInstance) -> "RepoBasicAuthHolder":
        return self.get(repo_id=repo_obj.get_identity(), repo_type=repo_obj.get_source_type(), module=module)


BasicAuth = namedtuple("BasicAuth", "username,password")


class RepoBasicAuthHolder(TimestampedModel):
    """Repo 鉴权"""

    username = models.CharField(verbose_name="仓库用户名", max_length=64)
    password = EncryptField(verbose_name="仓库密码")

    repo_id = models.IntegerField(verbose_name="关联仓库")
    repo_type = models.CharField(verbose_name="仓库类型", max_length=32)

    # 不同 module 相同 repo，保存多份账号密码
    module = models.ForeignKey("modules.Module", on_delete=models.CASCADE, verbose_name="蓝鲸应用模块")
    tenant_id = tenant_id_field_factory()

    objects = BasicAuthHolderManager()

    @property
    def basic_auth(self) -> BasicAuth:
        if not self.username and self.password:
            raise ValueError("basic auth require both username & password")

        return BasicAuth(self.username, self.password)

    @property
    def desensitized_info(self) -> dict:
        return dict(username=self.username)


class SourceTypeSpecConfigMgr(models.Manager):
    def build_configs(self) -> List:
        """根据 DB 数据，生成代码库配置"""
        return [c.to_dict() for c in self.all()]


class SourceTypeSpecConfig(AuditedModel):
    """SourceTypeSpec 数据存储

    [multi-tenancy] This model is not tenant-aware.
    """

    # Source Type Spec 配置
    name = models.CharField(verbose_name=_("服务名称"), unique=True, max_length=32)
    label = TranslatedFieldWithFallback(models.CharField(verbose_name="标签", max_length=32))
    enabled = models.BooleanField(verbose_name="是否启用", default=False)
    spec_cls = models.CharField(verbose_name="配置类路径", max_length=128)
    server_config = models.JSONField(verbose_name="服务配置", blank=True, default=dict)
    display_info = TranslatedFieldWithFallback(models.JSONField(verbose_name="展示信息", blank=True, default=dict))
    # OAuth Backend 配置
    authorization_base_url = models.CharField(verbose_name="OAuth 授权链接", default="", blank=True, max_length=256)
    client_id = models.CharField(verbose_name="OAuth App Client ID", default="", blank=True, max_length=256)
    client_secret = EncryptField(verbose_name="OAuth App Client Secret", default="", blank=True, max_length=256)
    redirect_uri = models.CharField(verbose_name="重定向（回调）地址", default="", blank=True, max_length=256)
    token_base_url = models.CharField(verbose_name="获取 Token 链接", default="", blank=True, max_length=256)
    oauth_display_info = TranslatedFieldWithFallback(
        models.JSONField(verbose_name="OAuth 展示信息", blank=True, default=dict)
    )

    objects = SourceTypeSpecConfigMgr()

    def to_dict(self):
        return {
            "attrs": {
                "name": self.name,
                "label": self.label,
                "enabled": self.enabled,
                "server_config": self.server_config,
                "display_info": self.display_info,
                "oauth_backend_config": {
                    "authorization_base_url": self.authorization_base_url,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,
                    "token_base_url": self.token_base_url,
                    "display_info": self.oauth_display_info,
                },
            },
            "spec_cls": self.spec_cls,
        }
