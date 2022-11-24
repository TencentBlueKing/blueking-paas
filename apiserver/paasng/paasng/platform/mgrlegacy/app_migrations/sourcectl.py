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

from paasng.dev_resources.sourcectl.connector import get_repo_connector
from paasng.dev_resources.sourcectl.package.uploader import upload_package_via_url
from paasng.dev_resources.sourcectl.source_types import get_sourcectl_names
from paasng.platform.core.storages.sqlalchemy import console_db
from paasng.platform.mgrlegacy.app_migrations.base import BaseMigration
from paasng.publish.sync_market.managers import AppManger, AppSecureInfoManger

logger = logging.getLogger(__name__)


class SourceControlMigration(BaseMigration):
    """Migrate source control data, only enabled for normal app(not s-mart app)

    - Create SvnRepository/SvnAccount object
    """

    def get_description(self):
        return "同步源码仓库"

    def should_skip(self):
        return self.legacy_app.is_saas

    def migrate(self):
        module = self.context.app.get_default_module()

        session = console_db.get_scoped_session()
        secure_info = AppSecureInfoManger(session).get(self.legacy_app.code)
        if not secure_info:
            logger.warning("app_secure_info module not found, skip migrate process.")
            return

        # Smart 应用需要将最近的部署包迁移过来
        if self.context.legacy_app_proxy.is_smart():
            package_info = AppManger(session).get_saas_package_info(self.legacy_app.id)
            # 应用没有源码包信息，则不需要处理
            if not package_info:
                return

            return upload_package_via_url(
                module,
                package_info.url,
                package_info.version,
                package_info.name,
                self.context.owner,
                need_patch=True,
                allow_overwrite=True,
            )

        # 获取仓库类型，并转换为 PaaS3.0的格式
        if secure_info.vcs_type == 0:
            repo_type = get_sourcectl_names().bare_git
        elif secure_info.vcs_type == 1:
            repo_type = get_sourcectl_names().bare_svn
        else:
            logger.warning(f"repo_type({secure_info.vcs_type}) not supported, skip migrate process.")
            return
        # 获取仓库链接和认证信息
        repo_url = secure_info.vcs_url
        repo_auth_info = {'username': secure_info.vcs_username, 'password': secure_info.vcs_password}

        # 绑定源码仓库信息到模块
        connector = get_repo_connector(repo_type, module)
        repo = connector.bind(repo_url, repo_auth_info=repo_auth_info)
        return repo

    def rollback(self):
        """
        回滚，解除仓库和模块间的关系即可，仓库可能被其他模块绑定，不能删除
        重置 module 相关字段即可，所以没有增加复杂度再封装到，不然要再查一次 paas2.0 的db获取 repo_type 信息
        """
        module = self.context.app.get_default_module()
        module.source_type = None
        module.source_repo_id = None
        module.save(update_fields=['source_type', 'source_repo_id'])
