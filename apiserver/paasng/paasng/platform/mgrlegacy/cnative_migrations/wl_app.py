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

from django.forms.models import model_to_dict

from paas_wl.bk_app.applications.models.app import WlApp
from paas_wl.bk_app.applications.models.config import Config
from paas_wl.bk_app.applications.models.release import Release
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.mgrlegacy.models import WlAppBackupRel


class WlAppBackupManager:
    def __init__(self, env: ModuleEnvironment):
        self.env = env
        self.original_wl_app = env.wl_app

    def create(self) -> WlApp:
        """create wl_app backup, include its latest config and latest release"""
        uuid_audited_fields = ["uuid", "created", "updated"]

        # 创建 WlApp 的副本
        wl_app_dict = model_to_dict(self.original_wl_app, exclude=uuid_audited_fields)
        wl_app_dict["name"] = f"{self.original_wl_app.name}-bak"
        wl_app = WlApp.objects.create(**wl_app_dict)

        # 建立备份关系
        WlAppBackupRel.objects.create(
            app_environment=self.env, original_id=self.original_wl_app.uuid, backup_id=wl_app.uuid
        )

        # 创建对应的 Config 副本
        config_dict = model_to_dict(self.original_wl_app.config_set.latest(), exclude=uuid_audited_fields + ["app"])
        config_dict["app"] = wl_app
        Config.objects.create(**config_dict)

        # 创建对应的 Release 副本
        try:
            release = Release.objects.get_latest(self.original_wl_app)
            release_dict = model_to_dict(release, exclude=uuid_audited_fields + ["app"])
            release_dict["app"] = wl_app
            Release.objects.create(**release_dict)
        except Release.DoesNotExist:
            pass

        return wl_app

    def delete(self):
        """delete wl_app backup from db, delete backup relationship at the same time"""
        # config and release will be deleted by cascade
        rel = WlAppBackupRel.objects.get(original_id=self.original_wl_app.uuid)
        WlApp.objects.filter(uuid=rel.backup_id).delete()
        rel.delete()

    def get(self) -> WlApp:
        """get wl_app backup from db"""
        rel = WlAppBackupRel.objects.get(original_id=self.original_wl_app.uuid)
        return WlApp.objects.get(uuid=rel.backup_id)
