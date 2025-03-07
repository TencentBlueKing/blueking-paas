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
import typing

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import cached_property
from rest_framework.exceptions import PermissionDenied

from paas_wl.infras.cluster.models import Cluster
from paasng.accessories.publish.sync_market.managers import AppDeveloperManger
from paasng.core.region.models import get_region
from paasng.platform.applications.constants import AppLanguage
from paasng.platform.applications.models import Application
from paasng.platform.mgrlegacy.constants import LegacyAppTag, MigrationStatus
from paasng.platform.mgrlegacy.models import MigrationProcess

try:
    from paasng.platform.mgrlegacy.legacy_proxy_te import LegacyAppProxy
except ImportError:
    from paasng.platform.mgrlegacy.legacy_proxy import LegacyAppProxy  # type: ignore

logger = logging.getLogger(__name__)


def check_operation_perms(username, legacy_app_id, session):
    legacy_apps = AppDeveloperManger(session).get_apps_by_developer(username)
    _ids = [legacy_app.id for legacy_app in legacy_apps]
    if legacy_app_id not in _ids:
        raise PermissionDenied("You are not allowed to do this operation.")


class LegacyAppManager:
    def __init__(self, legacy_app, session):
        self.legacy_app = legacy_app
        self.legacy_app_proxy = LegacyAppProxy(legacy_app=self.legacy_app, session=session)
        self.migration_process = MigrationProcess.objects.filter(legacy_app_id=self.legacy_app.id).last()

    def is_finished_migration(self):
        return (
            self.migration_process is not None
            and self.migration_process.rollbacked is False
            and self.migration_process.confirmed is True
        )

    def get_latest_migration_id(self):
        return None if self.migration_process is None else self.migration_process.id

    def is_active(self):
        return None if self.migration_process is None else self.migration_process.is_active()

    def legacy_app_logo(self):
        return self.legacy_app.logo

    def region(self):
        try:
            region = self.legacy_app_proxy.to_paasv3_region()
        except ValueError:
            return self.legacy_app.deploy_ver
        return get_region(region).display_name

    @cached_property
    def app_migration_tag(self) -> typing.Tuple[str, typing.List[str]]:
        if not MigrationProcess.objects.filter(legacy_app_id=self.legacy_app.id).exists():
            reasons = self.legacy_app_proxy.is_supported()
            if reasons:
                return LegacyAppTag.NOT_SUPPORT.value, reasons
            return LegacyAppTag.SUPPORT.value, []
        elif self.migration_process is not None and self.migration_process.app is not None:
            # FIXME: change status
            # if self.migration_process.status == MigrationStatus.CONFIRMED.value:
            if self.migration_process.confirmed:
                return LegacyAppTag.FINISHED_MIGRATION.value, []
            else:
                return LegacyAppTag.ON_MIGRATION.value, []
        else:
            return LegacyAppTag.SUPPORT.value, []

    def is_ready_for_migration(self):
        """准备迁往V3的应用"""
        tag, _ = self.app_migration_tag
        # return state in [LegacyAppTag.ON_MIGRATION.value, LegacyAppTag.SUPPORT.value]
        # NOTE: on_migration should not be seen in ready list again?
        return tag in [LegacyAppTag.SUPPORT.value, LegacyAppTag.ON_MIGRATION.value]

    def is_done_migration(self):
        """已经迁往V3的应用"""
        return self.is_finished_migration()

    @cached_property
    def category(self):
        category_map = {
            "is_ready_for_migration": "todoMigrate",
            "is_done_migration": "doneMigrate",
            "is_not_supported_migration": "cannotMigrate",
        }
        for method, value in category_map.items():
            if getattr(self, method)():
                return value
        raise NotImplementedError("state not found")

    def is_not_supported_migration(self):
        tag, _ = self.app_migration_tag
        return tag in [LegacyAppTag.NOT_SUPPORT.value]

    def get_logo_url(self):
        if (
            self.migration_process is not None
            and self.migration_process.status == MigrationStatus.CONFIRMED.value
            and
            # 避免迁移应用被删除时, 整个接口挂掉
            Application.objects.filter(code=self.legacy_app.code).exists()
        ):
            app = Application.objects.get(code=self.legacy_app.code)
            return app.get_logo_url()
        else:
            return self.legacy_app_proxy.get_logo_url()

    def has_prod_deployed_before_migration(self):
        # 为了防止未上线过的应用迁移完成后有又回滚，这里的部署状态需要用当时的迁移时状态进行判断
        # 否则，可能出现这种漏洞，迁移前时为上线状态，迁移后用户把应用上线了，就可以回滚了
        if self.migration_process is not None and all(
            [
                self.migration_process.status == MigrationStatus.CONFIRMED.value,
                self.migration_process.legacy_app_has_all_deployed is False,
            ]
        ):
            has_prod_deployed = False
        else:
            has_prod_deployed = self.legacy_app_proxy.has_prod_deployed()
        return has_prod_deployed

    def serialize_data(self):
        tag, not_support_reasons = self.app_migration_tag

        return {
            "category": self.category,
            "legacy_app_id": self.legacy_app.id,
            "code": self.legacy_app.code,
            "name": self.legacy_app.name,
            "logo": self.get_logo_url(),
            "tag": tag,
            "not_support_reasons": not_support_reasons,
            "language": self.legacy_app.language,
            "created": self.legacy_app.created_date,
            "latest_migration_id": self.get_latest_migration_id(),
            "finished_migration": self.is_finished_migration(),
            "is_active": self.is_active(),
            "migration_finished_date": self.get_migration_finished_date(),
            "is_prod_deployed": self.legacy_app_proxy.is_prod_deployed(),  # 用于展示是否已上架
            "has_prod_deployed_before_migration": self.has_prod_deployed_before_migration(),  # 用于控制迁移完成回滚
            "region": self.region(),
            "legacy_url": self.legacy_app_proxy.legacy_url(),
        }

    def get_language(self):
        """将桌面的开发语言转换成v3上的开发语言, 两者大小写有些出入"""
        language_lower = self.legacy_app.language.lower()
        if language_lower in ["python"]:
            return AppLanguage.PYTHON.value
        elif language_lower in ["php"]:
            return AppLanguage.PHP.value
        elif language_lower in ["java"]:
            return AppLanguage.JAVA.value
        else:
            raise ValueError(language_lower)

    def get_migration_finished_date(self):
        if self.migration_process and self.migration_process.status == MigrationStatus.CONFIRMED.value:
            return self.migration_process.confirmed_date

        return None


def get_cnative_target_cluster() -> Cluster:
    """
    Get the target cluster when migrating an application to the cloud-native type.

    :raises: ImproperlyConfigured if MGRLEGACY_CLOUD_NATIVE_TARGET_CLUSTER is not configured.
    :return: migrate to cnative application's target cluster.
    """
    target_cluster_name = settings.MGRLEGACY_CLOUD_NATIVE_TARGET_CLUSTER

    if not target_cluster_name:
        raise ImproperlyConfigured("MGRLEGACY_CLOUD_NATIVE_TARGET_CLUSTER is not configured.")

    return Cluster.objects.get(name=target_cluster_name)
