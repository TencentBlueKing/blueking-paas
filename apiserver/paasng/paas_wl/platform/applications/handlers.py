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
from django.db.models.signals import post_save
from django.dispatch import receiver

from paas_wl.platform.applications.models import Config, WlApp
from paas_wl.platform.applications.models.managers.app_res_ver import AppResVerManager
from paas_wl.resources.base.generation import get_latest_mapper_version


@receiver(post_save, sender=WlApp)
def on_app_created(sender, instance, created, *args, **kwargs):
    """Do extra things when an app was created"""
    if created:
        create_initial_config(instance)
        set_res_ver(instance)


def create_initial_config(app: WlApp):
    """Make sure the initial Config was created"""
    try:
        app.config_set.latest()
    except Config.DoesNotExist:
        Config.objects.create(app=app, owner=app.owner, runtime={})


def set_res_ver(app: WlApp):
    # mapper version 概念应该只在 engine 中消化，当前在应用新建后更新
    latest_version = get_latest_mapper_version().version
    AppResVerManager(app).update(latest_version)
