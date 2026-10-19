# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

import json
import logging
from dataclasses import dataclass
from typing import Dict, Optional

from django.conf import settings
from paas_service.base_vendor import BaseProvider, InstanceData
from paas_service.constants import DEFAULT_TENANT_ID
from paas_service.utils import gen_unique_id, generate_password

from svc_bk_repo.vendor.helper import BKGenericRepoManager, RequestError

logger = logging.getLogger(__name__)

# 蓝鲸制品库(bkrepo)的错误码.
#
# NOTE: 不同版本的 bkrepo 错误码并不一致:
#   - 仓库已存在: 新版本 251007, 旧版本 251008
#   - 仓库不存在: 新版本 251006, 旧版本 251007
#   - 用户不存在: 250202
REPO_EXISTS_ERROR_CODES = frozenset({"251007", "251008"})
REPO_NOT_FOUND_ERROR_CODES = frozenset({"251006", "251007"})
USER_NOT_FOUND_ERROR_CODES = frozenset({"250202"})


@dataclass
class Provider(BaseProvider):
    endpoint_url: str
    username: str
    password: str
    project: str
    quota: Optional[int] = settings.BKREPO_DEFAULT_QUOTA

    SERVICE_NAME = "bkrepo"

    def make_manager(self, tenant_id: str) -> BKGenericRepoManager:
        """Create a new BKGenericRepoManager instance with the given tenant_id."""
        manager = BKGenericRepoManager(
            endpoint_url=self.endpoint_url,
            username=self.username,
            password=self.password,
            project=self.project,
            tenant_id=tenant_id,
        )
        return manager

    def create(self, params: Dict) -> InstanceData:
        """
        创建增强服务

        :param params: Dict, 由 v3 申请增强服务实例时透传
        engine_app_name: str
        app_members: List[str]
        """
        preferred_name = params.get("engine_app_name")
        association_users = json.loads(params.get("app_developers", "[]"))
        tenant_id = params.get("tenant_id")
        username = repo_suffix = gen_unique_id(preferred_name)
        public_repo = f"public-{repo_suffix}"
        private_repo = f"private-{repo_suffix}"
        password = generate_password()

        manager = self.make_manager(tenant_id=tenant_id)

        try:
            manager.create_repo(repo=public_repo, public=True, quota=self.quota)
        except RequestError as e:
            # 仓库已存在: 251007(新版本) / 251008(旧版本)
            if str(e.code) not in REPO_EXISTS_ERROR_CODES:
                raise

        try:
            manager.create_repo(repo=private_repo, public=False, quota=self.quota)
        except RequestError as e:
            # 仓库已存在: 251007(新版本) / 251008(旧版本)
            if str(e.code) not in REPO_EXISTS_ERROR_CODES:
                raise

        manager.create_user(
            repo=public_repo, username=username, password=password, association_users=association_users
        )
        manager.create_user(
            repo=private_repo, username=username, password=password, association_users=association_users
        )
        return InstanceData(
            credentials={
                "username": username,
                "password": password,
                # 保持 bucket 字段, 向前兼容
                "bucket": private_repo,
                # 新增区分 `公开` 仓库和 `私有` 仓库的字段
                "private_bucket": private_repo,
                "public_bucket": public_repo,
                "endpoint_url": manager.endpoint_url,
                "project": manager.project,
            },
            config={
                "association_users": association_users,
                "bucket": private_repo,
                "private_bucket": private_repo,
                "public_bucket": public_repo,
                "project": manager.project,
                "tenant_id": tenant_id,
            },
        )

    def delete(self, instance_data: InstanceData):
        """回收实例占用的 bkrepo 资源: 私有仓库, 公开仓库, 用户"""
        private_bucket = instance_data.credentials["private_bucket"]
        public_bucket = instance_data.credentials["public_bucket"]
        username = instance_data.credentials["username"]
        tenant_id = self._resolve_tenant_id(instance_data)

        manager = self.make_manager(tenant_id=tenant_id)
        self._delete_user(manager, username)
        self._delete_repo(manager, private_bucket)
        self._delete_repo(manager, public_bucket)

    def _delete_user(self, manager: BKGenericRepoManager, username: str) -> None:
        """删除用户, 用户已不存在时视作回收完成(支持重复回收)"""
        try:
            manager.delete_user(username=username)
        except RequestError as e:
            if str(e.code) not in USER_NOT_FOUND_ERROR_CODES:
                raise
            logger.info("bkrepo user<%s> not found, skip deleting", username)

    def _delete_repo(self, manager: BKGenericRepoManager, repo: str) -> None:
        """删除仓库, 仓库已不存在时视作回收完成(支持重复回收)"""
        try:
            manager.delete_repo(repo=repo, forced=True)
        except RequestError as e:
            if str(e.code) not in REPO_NOT_FOUND_ERROR_CODES:
                raise
            logger.info("bkrepo repository<%s> not found, skip deleting", repo)

    def patch(self, instance_data: InstanceData, params: Dict) -> InstanceData:
        username = instance_data.credentials["username"]
        password = instance_data.credentials["password"]
        association_users = instance_data.config["association_users"] = json.loads(params.get("app_developers", "[]"))
        tenant_id = self._resolve_tenant_id(instance_data)

        manager = self.make_manager(tenant_id=tenant_id)
        manager.update_user(username=username, password=password, association_users=association_users)
        return instance_data

    def _resolve_tenant_id(self, instance_data: InstanceData) -> str:
        """解析实例访问 BKRepo 时应携带的租户 ID.

        老实例的 config 中缺失 tenant_id，回退到平台默认租户。
        """
        return instance_data.config.get("tenant_id") or DEFAULT_TENANT_ID
