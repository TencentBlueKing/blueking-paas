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
import logging
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from blue_krill.storages.blobstore.bkrepo import BKGenericRepo, BKRepoManager, RepositoryType, RequestError
from django.conf import settings
from django.core.management.base import BaseCommand

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
    # TODO: engine 支持创建 secret 后调整成 private
    Repo(name="docker", type=RepositoryType.DOCKER, public=True),
    Repo(name="pypi", type=RepositoryType.PYPI, public=True),
    Repo(name="npm", type=RepositoryType.NPM, public=True),
]

BUILTIN_APP_TMPLS = {
    assets_path / "dj_auth_template_blueapps_dj2.tar.gz": "open/dj_auth_template_blueapps_dj2.tar.gz",
    assets_path / "node-js-bk-magic-vue-spa.tar.gz": "open/node-js-bk-magic-vue-spa.tar.gz",
    assets_path / "dj_with_hello_world_dj2.tar.gz": "open/dj_with_hello_world_dj2.tar.gz",
}


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
        logger.info("即将创建 bkrepo 项目: %s", self.bkpaas_project)
        with allow_resource_exists():
            dry_run or manager.create_project(self.bkpaas_project)

        # 创建增强服务项目
        logger.info("即将创建 bkrepo 项目: %s", addons_project)
        with allow_resource_exists():
            dry_run or manager.create_project(addons_project)

        # 创建用户
        # 创建 PaaS3.0 用户
        logger.info("即将创建 bkrepo 用户: %s", bkpaas3_username)
        dry_run or manager.create_user_to_project(
            username=bkpaas3_username, password=bkpaas3_password, association_users=[], project=self.bkpaas_project
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

        tmpls_repo = self.get_tmpls_repo(bkpaas3_username, bkpaas3_password)
        for filepath, key in BUILTIN_APP_TMPLS.items():
            if filepath.exists():
                logger.info("即将上传开发框架模板至 %s", key)
                dry_run or tmpls_repo.upload_file(Path(filepath), key, allow_overwrite=True)
            else:
                logger.warning("源码模板不存在! 请检查 %s", filepath)

        logger.info("初始化 bkrepo 成功")

    @staticmethod
    def get_manager(username: str, password: str):
        config = settings.BLOBSTORE_BKREPO_CONFIG
        return BKRepoManager(
            endpoint_url=config["ENDPOINT"],
            username=username,
            password=password,
        )

    @staticmethod
    def get_tmpls_repo(username: str, password: str):
        config = settings.BLOBSTORE_BKREPO_CONFIG
        return BKGenericRepo(
            bucket=settings.BLOBSTORE_BUCKET_TEMPLATES,
            project=config["PROJECT"],
            endpoint_url=config["ENDPOINT"],
            username=username,
            password=password,
        )

    @property
    def bkpaas_project(self):
        return settings.BLOBSTORE_BKREPO_CONFIG["PROJECT"]
