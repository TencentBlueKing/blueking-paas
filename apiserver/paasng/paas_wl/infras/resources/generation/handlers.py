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

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.infras.resources.generation.version import AppResVerManager, get_latest_mapper_version


@receiver(post_save, sender=WlApp)
def set_default_version(sender, instance, created, *args, **kwargs):
    """Set the default resource generation version for new application."""
    if created:
        # mapper version 概念应该只在 engine 中消化，当前在应用新建后更新
        latest_version = get_latest_mapper_version().version
        AppResVerManager(instance).update(latest_version)
