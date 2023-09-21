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
from blue_krill.async_utils.poll_task import PollingResult, TaskPoller
from celery import shared_task

from paasng.pluginscenter.constants import PluginReleaseStatus
from paasng.pluginscenter.models import PluginInstance, PluginRelease, PluginReleaseStage
from paasng.pluginscenter.releases.stages import init_stage_controller


class ReleaseStatusPoller(TaskPoller):
    def query(self) -> PollingResult:
        plugin = PluginInstance.objects.get(pd__identifier=self.params["pd_id"], id=self.params["plugin_id"])
        release = PluginRelease.objects.get(plugin=plugin, id=self.params["release_id"])
        if release.current_stage_id != self.params["stage_id"]:
            return PollingResult.done()

        if release.status not in PluginReleaseStatus.running_status():
            return PollingResult.done()

        ctrl = init_stage_controller(release.current_stage)
        if not ctrl.async_check_status():
            return PollingResult.doing()
        return PollingResult.done()


@shared_task
def poll_stage_status(plugin: PluginInstance, release: PluginRelease, stage: PluginReleaseStage):
    ReleaseStatusPoller.start(
        params={
            "pd_id": plugin.pd.identifier,
            "plugin_id": plugin.id,
            "release_id": release.pk,
            "stage_id": stage.pk,
        }
    )
