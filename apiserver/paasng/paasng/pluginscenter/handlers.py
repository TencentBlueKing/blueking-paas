"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from paasng.pluginscenter.constants import PluginReleaseStatus
from paasng.pluginscenter.models import PluginReleaseStage


@receiver(post_save, sender=PluginReleaseStage)
def update_release_status_when_stage_status_change(sender, instance: PluginReleaseStage, created, *args, **kwargs):
    if created:
        return
    release = instance.release
    # 发布中断或失败
    if instance.status in PluginReleaseStatus.abnormal_status():
        release.status = instance.status
        release.save()
    # 最后一个步骤成功, 即发布成功
    elif instance.status == PluginReleaseStatus.SUCCESSFUL and instance.next_stage is None:
        release.status = instance.status
        release.save()
