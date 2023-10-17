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

from django.utils.translation import gettext_lazy as _

from paasng.accessories.publish.sync_market.utils import set_migrated_state
from paasng.core.signals import post_change_app_router, rollback_change_app_router

from .base import BaseMigration

logger = logging.getLogger(__name__)


class EntranceMigration(BaseMigration):
    def get_description(self):
        return _("换桌面入口")

    def migrate(self):
        """执行切换操作，如抛出异常，则会执行回滚操作
        2021-01-29 note: 之前的版本迁移确认时，PaaS 2.0 上下架失败，还是会修改应用的状态，导致应用在 PaaS2.0 页面上看不到，但是进程可能还在
        """
        # 修改入口 to new entrance
        set_migrated_state(self.context.legacy_app.code, True)

        # 同步数据到桌面（logo & 访问地址）
        post_change_app_router.send(
            sender=self,
            application=self.context.app,
            legacy_app=self.legacy_app,
            migration_process=self.context.migration_process,
        )

    def rollback(self):
        # 修改入口, to old entrance
        set_migrated_state(self.context.legacy_app.code, False)
        self.add_log(_('应用接入层已经回滚到 PaaS2.0'))

        # 回滚差异数据（logo & 访问地址）
        rollback_change_app_router.send(
            sender=self,
            application=self.context.app,
            legacy_app=self.legacy_app,
            migration_process=self.context.migration_process,
        )
