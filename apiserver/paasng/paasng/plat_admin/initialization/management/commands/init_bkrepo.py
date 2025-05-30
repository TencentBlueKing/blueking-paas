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
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from blue_krill.storages.blobstore.bkrepo import BKRepoManager, RepositoryType, RequestError
from django.conf import settings
from django.core.management.base import BaseCommand

from paasng.core.tenant.user import OP_TYPE_TENANT_ID
from paasng.utils.validators import str2bool

logger = logging.getLogger(__name__)
assets_path = Path(__file__).parents[5] / "assets"


@dataclass
class Repo:
    name: str
    type: RepositoryType = RepositoryType.GENERIC
    public: bool = False


BUILTIN_REPOS = [
    Repo(name=settings.SERVICE_LOGO_BUCKET, type=RepositoryType.GENERIC, public=True),
    Repo(name=settings.APP_LOGO_BUCKET, type=RepositoryType.GENERIC, public=True),
    Repo(name=settings.BLOBSTORE_BUCKET_APP_SOURCE, type=RepositoryType.GENERIC, public=False),
    Repo(name=settings.BLOBSTORE_BUCKET_TEMPLATES, type=RepositoryType.GENERIC, public=False),
    Repo(name=settings.BLOBSTORE_BUCKET_AP_PACKAGES, type=RepositoryType.GENERIC, public=False),
    Repo(name="docker", type=RepositoryType.DOCKER, public=False),
    Repo(name="pypi", type=RepositoryType.PYPI, public=True),
    Repo(name="npm", type=RepositoryType.NPM, public=True),
    # bk-apigateway 复用 bkpaas 仓库:
    #  Q: 为什么要在开发者中心初始化而不是在网关侧初始化？
    #  A: bkrepo 上的 bkpaas 项目是在开发者中心部署的时候创建的。
    #   私有化版本部署时先部署网关再部署开发者中心，故统一放到开发者中心减少部署依赖。
    #   以下是网关 java/go sdk 需要
    Repo(name="maven", type=RepositoryType.MAVEN, public=True),
    Repo(name="generic", type=RepositoryType.GENERIC, public=True),
]


@contextmanager
def allow_resource_exists():
    try:
        yield
    except RequestError as e:
        # 旧版本: 项目已存在: 251006
        # 旧版本: 仓库已存在: 251008
        # 项目已存在: 251005
        # 仓库已存在: 251007
        logger.debug(f"错误码: {e.code}")
        if str(e.code) in ["251005", "251007"]:
            pass
        elif str(e.code) in ["251006", "251008"]:
            logger.warning("[deprecated] 捕获到可能是旧版本的蓝鲸制品库(bkrepo)的错误码, 忽略.")
        else:
            raise


class Command(BaseCommand):
    help = "初始化 bkrepo"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", dest="dry_run", default=True, type=str2bool, help="避免意外触发, 若想执行需添加该参数"
        )
        parser.add_argument("--init-enabled", dest="init_enabled", type=str2bool, required=True, default=True)
        parser.add_argument("--super-username", dest="super_username", required=True)
        parser.add_argument("--super-password", dest="super_password", required=True)
        parser.add_argument("--bkpaas3-username", dest="bkpaas3_username", required=True)
        parser.add_argument("--bkpaas3-password", dest="bkpaas3_password", required=True)
        parser.add_argument("--addons-username", dest="addons_username", required=True)
        parser.add_argument("--addons-password", dest="addons_password", required=True)
        parser.add_argument("--addons-project", dest="addons_project", required=False, default="bksaas-addons")
        parser.add_argument(
            "--addons-project-name", dest="addons_project_name", required=False, default="bksaas-addons"
        )
        parser.add_argument("--lesscode-username", dest="lesscode_username", required=True)
        parser.add_argument("--lesscode-password", dest="lesscode_password", required=True)

    def handle(
        self,
        dry_run: bool,
        init_enabled: bool,
        super_username: str,
        super_password: str,
        bkpaas3_username,
        bkpaas3_password,
        addons_username,
        addons_password,
        addons_project,
        addons_project_name,
        lesscode_username,
        lesscode_password,
        **kwargs,
    ):
        # 未开启，则不执行
        if not init_enabled:
            logger.info(f"init_enabled is set to {init_enabled}, skip init bkrepo")
            return

        # 当且仅当 adminUsername 和 adminPassword 不为空时，会初始化 bkrepo 账号和仓库
        if not (super_username and super_password):
            logger.info("super_username or super_password is empty, skip init bkrepo")
            return

        logger.info("开始初始化 bkrepo")
        manager = self.get_manager(super_username, super_password)
        # 创建项目
        # 创建 PaaS3.0 项目
        logger.info("即将创建 bkrepo 项目: %s", self.bkpaas_project_name)
        with allow_resource_exists():
            dry_run or manager.create_project(self.bkpaas_project_name)

        # 创建增强服务项目
        logger.info("即将创建 bkrepo 项目: %s", addons_project_name)
        with allow_resource_exists():
            dry_run or manager.create_project(addons_project_name)

        # 创建用户
        # 创建 PaaS3.0 用户
        logger.info("即将创建 bkrepo 用户: %s", bkpaas3_username)
        dry_run or manager.create_user_to_project(
            username=bkpaas3_username,
            password=bkpaas3_password,
            association_users=[],
            project=self.bkpaas_project,
        )
        # 创建增强服务用户
        logger.info("即将创建 bkrepo 用户: %s", addons_username)
        dry_run or manager.create_user_to_project(
            username=addons_username,
            password=addons_password,
            association_users=[],
            project=addons_project,
        )

        # 创建 PaaS3.0 仓库
        for repo in BUILTIN_REPOS:
            logger.info("即将创建 bkrepo 的仓库: %s", repo)
            with allow_resource_exists():
                dry_run or manager.create_repo(
                    project=self.bkpaas_project, repo=repo.name, repo_type=repo.type, public=repo.public
                )

        # 创建 LessCode 用户
        logger.info("即将创建 bkrepo 用户: bklesscode")
        dry_run or manager.create_user_to_repo(
            username=lesscode_username,
            password=lesscode_password,
            association_users=[],
            project=self.bkpaas_project,
            repo="npm",
        )

        logger.info("初始化 bkrepo 成功")

    @staticmethod
    def get_manager(username: str, password: str):
        config = settings.BLOBSTORE_BKREPO_CONFIG
        return BKRepoManager(
            endpoint_url=config["ENDPOINT"],
            username=username,
            password=password,
            tenant_id=OP_TYPE_TENANT_ID if settings.ENABLE_MULTI_TENANT_MODE else None,
        )

    @property
    def bkpaas_project(self):
        return settings.BLOBSTORE_BKREPO_CONFIG["PROJECT"]

    @property
    def bkpaas_project_name(self):
        return settings.BLOBSTORE_BKREPO_PROJECT_NAME
