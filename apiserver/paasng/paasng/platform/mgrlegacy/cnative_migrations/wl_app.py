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
from typing import Optional

from django.db import transaction
from django.forms.models import model_to_dict

from paas_wl.bk_app.applications.models.app import WlApp
from paas_wl.bk_app.applications.models.config import Config
from paas_wl.bk_app.applications.models.release import Release
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.mgrlegacy.entities import DefaultAppLegacyData
from paasng.platform.mgrlegacy.exceptions import PreCheckMigrationFailed
from paasng.platform.mgrlegacy.models import WlAppBackupRel

from .base import CNativeBaseMigrator


class WlAppBackupMigrator(CNativeBaseMigrator):
    def _can_migrate_or_raise(self):
        if self.app.type != ApplicationType.DEFAULT.value:
            raise PreCheckMigrationFailed(f"app({self.app.code}) type is not default")

    def _generate_legacy_data(self) -> Optional[DefaultAppLegacyData]:
        """generate legacy data"""
        return None

    def _migrate(self):
        """迁移备份 wl_app"""
        for m in self.app.modules.all():
            for env in m.envs.all():
                WlAppBackupManager(env).create()

    def _rollback(self):
        """回滚删除 wl_app 备份"""
        for m in self.app.modules.all():
            for env in m.envs.all():
                WlAppBackupManager(env).delete()


class WlAppBackupManager:
    """WlApp 备份管理器"""

    def __init__(self, env: ModuleEnvironment):
        self.env = env
        self.original_wl_app = env.wl_app
        self.backup_name = f"{self.original_wl_app.name}--bak"

    def create(self) -> WlApp:
        """create wl_app backup, include its latest config and latest release"""
        with transaction.atomic(using="default"), transaction.atomic(using="workloads"):
            uuid_audited_fields = ["uuid", "created", "updated"]

            # 创建 WlApp 的副本
            wl_app_dict = model_to_dict(self.original_wl_app, exclude=uuid_audited_fields)
            wl_app_dict["name"] = self.backup_name
            wl_app = WlApp.objects.create(**wl_app_dict)

            # 建立备份关系
            WlAppBackupRel.objects.create(
                app_environment=self.env, original_id=self.original_wl_app.uuid, backup_id=wl_app.uuid
            )

            # 创建对应的 Config 副本. 用于 get_cluster_by_app 中 app.config_set.latest().cluster 逻辑
            config_dict = model_to_dict(
                self.original_wl_app.config_set.latest(), exclude=uuid_audited_fields + ["app"]
            )
            # WlApp 创建后(post_save), on_app_created handler 会创建 Config, 因此这里使用 update_or_create
            Config.objects.update_or_create(**config_dict, defaults={"app": wl_app})

            # 创建对应的 Release 副本. 用于 get_mapper_proc_config_latest 中 Release.objects.get_latest(app) 逻辑.
            # 虽然云原生应用部署时未创建 Release 对象, 但 get_mapper_proc_config_latest 中返回的 MapperProcConfig 含有 wl_app 属性,
            # 为了调用 get_mapper_proc_config_latest 的一致性, 这里需要备份 Release
            try:
                release = Release.objects.get_latest(self.original_wl_app)
                release_dict = model_to_dict(release, exclude=uuid_audited_fields + ["app"])
                release_dict.update({"app": wl_app, "build": release.build, "config": release.config})
                Release.objects.create(**release_dict)
            except Release.DoesNotExist:
                pass

            # 将 scheduler_safe_name 设置成原备份数据的 scheduler_safe_name 值, 以便正确处理 namespace 等调度配置
            setattr(wl_app, "scheduler_safe_name", self.original_wl_app.scheduler_safe_name)
            return wl_app

    def delete(self):
        """delete wl_app backup from db, delete backup relationship at the same time"""
        with transaction.atomic(using="default"), transaction.atomic(using="workloads"):
            # config and release will be deleted by cascade
            try:
                rel = WlAppBackupRel.objects.get(original_id=self.original_wl_app.uuid)
            except WlAppBackupRel.DoesNotExist:
                WlApp.objects.filter(name=self.backup_name, region=self.original_wl_app.region).delete()
            else:
                WlApp.objects.filter(uuid=rel.backup_id).delete()
                rel.delete()

    def get(self) -> WlApp:
        """get wl_app backup from db"""
        rel = WlAppBackupRel.objects.get(original_id=self.original_wl_app.uuid)
        wl_app_backup = WlApp.objects.get(uuid=rel.backup_id)

        # 读取备份对象时, 需要将 scheduler_safe_name 设置成原备份数据的 scheduler_safe_name 值, 以便正确处理 namespace 等调度配置
        # 相当于去除了 --bak 后缀
        setattr(wl_app_backup, "scheduler_safe_name", self.original_wl_app.scheduler_safe_name)
        return wl_app_backup
