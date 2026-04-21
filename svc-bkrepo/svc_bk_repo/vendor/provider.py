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

import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

from django.conf import settings
from paas_service.base_vendor import BaseProvider, InstanceData
from paas_service.utils import gen_unique_id, generate_password

from svc_bk_repo.vendor.helper import BKGenericRepoManager, RequestError

logger = logging.getLogger(__name__)


class BKRepoErrorCode(str, Enum):
    REPO_EXISTS = "251008"


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
            # 仓库已存在: 251008
            if str(e.code) not in [BKRepoErrorCode.REPO_EXISTS]:
                raise

        try:
            manager.create_repo(repo=private_repo, public=False, quota=self.quota)
        except RequestError as e:
            # 仓库已存在: 251008
            if str(e.code) not in [BKRepoErrorCode.REPO_EXISTS]:
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
        repo = instance_data.credentials["repo"]
        username = instance_data.credentials["username"]
        tenant_id = instance_data.config["tenant_id"]

        manager = self.make_manager(tenant_id=tenant_id)
        manager.delete_user(username=username)
        manager.delete_repo(repo=repo, forced=True)

    def patch(self, instance_data: InstanceData, params: Dict) -> InstanceData:
        username = instance_data.credentials["username"]
        password = instance_data.credentials["password"]
        association_users = instance_data.config["association_users"] = json.loads(params.get("app_developers", "[]"))
        tenant_id = instance_data.config["tenant_id"]

        manager = self.make_manager(tenant_id=tenant_id)
        manager.update_user(username=username, password=password, association_users=association_users)
        return instance_data
