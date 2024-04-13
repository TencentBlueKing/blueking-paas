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

from paas_wl.bk_app.applications.models.app import NAME_BAK_SUFFIX, WlApp
from paas_wl.bk_app.applications.models.config import Config
from paas_wl.bk_app.applications.models.release import Release


class WlAppBackupManager:
    def __init__(self, original_wl_app: WlApp):
        self.original_wl_app = original_wl_app
        self.bak_name = f"{original_wl_app.name}{NAME_BAK_SUFFIX}"

    def create(self) -> WlApp:
        """create wl_app backup, include its latest config and latest release"""
        uuid_audited_fields = ["uuid", "created", "updated"]

        # 创建 WlApp 的副本
        wl_app_dict = model_to_dict(self.original_wl_app, exclude=uuid_audited_fields)
        wl_app_dict["name"] = self.bak_name
        wl_app = WlApp.objects.create(**wl_app_dict)

        # 创建对应的 Config 副本
        config_dict = model_to_dict(self.original_wl_app.config_set.latest(), exclude=uuid_audited_fields + ["app"])
        config_dict["app"] = wl_app
        Config.objects.create(**config_dict)

        # 创建对应的 Release 副本
        release = Release.objects.get_latest(self.original_wl_app)
        release_dict = model_to_dict(release, exclude=uuid_audited_fields + ["app"])
        release_dict["app"] = wl_app
        Release.objects.create(**release_dict)

        return wl_app

    def delete(self):
        """delete wl_app backup from db"""
        # config and release will be deleted by cascade
        WlApp.objects.filter(region=self.original_wl_app.region, name=self.bak_name).delete()

    def get(self) -> WlApp:
        """get wl_app backup from db"""
        return WlApp.objects.get(region=self.original_wl_app.region, name=self.bak_name)
