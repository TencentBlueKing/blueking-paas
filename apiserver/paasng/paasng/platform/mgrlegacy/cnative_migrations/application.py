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

from typing import Optional

from paas_wl.bk_app.applications.constants import WlAppType
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import Application
from paasng.platform.mgrlegacy.entities import DefaultAppLegacyData
from paasng.platform.mgrlegacy.exceptions import PreCheckMigrationFailed

from .base import CNativeBaseMigrator


class ApplicationTypeMigrator(CNativeBaseMigrator):
    """ApplicationTypeMigrator to migrate the type field of application and wl_app"""

    def _generate_legacy_data(self) -> Optional[DefaultAppLegacyData]:
        legacy_data: DefaultAppLegacyData = self.migration_process.legacy_data
        legacy_data.app_type = self.app.type
        return legacy_data

    def _can_migrate_or_raise(self):
        if self.app.type != ApplicationType.DEFAULT.value:
            raise PreCheckMigrationFailed(f"app({self.app.code}) type is not default")

    def _migrate(self):
        """migrate the type field of application and wl_app to cloud_native"""
        self.app.type = ApplicationType.CLOUD_NATIVE.value
        self.app.save(update_fields=["type"])
        self._update_wl_app_type(self.app)

    def _rollback(self):
        """rollback the type field of application and wl_app to legacy data"""
        self.app.type = self.migration_process.legacy_data.app_type
        self.app.save(update_fields=["type"])
        self._update_wl_app_type(self.app)

    def _update_wl_app_type(self, app: Application):
        wl_app_type = self._get_wl_app_type(app)

        for m in app.modules.all():
            for env in m.envs.all():
                wl_app = env.wl_app
                wl_app.type = wl_app_type
                wl_app.save(update_fields=["type"])

    def _get_wl_app_type(self, app: Application) -> str:
        return WlAppType.CLOUD_NATIVE if app.type == ApplicationType.CLOUD_NATIVE else WlAppType.DEFAULT
