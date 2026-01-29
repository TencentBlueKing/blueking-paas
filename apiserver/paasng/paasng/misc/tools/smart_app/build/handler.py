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
from dataclasses import dataclass, field
from typing import Any, Dict, List

from attrs import define
from django.conf import settings

from paas_wl.bk_app.deploy.app_res.controllers import PodScheduleHandler
from paas_wl.infras.resources.base.exceptions import ResourceDuplicate, ResourceMissing
from paas_wl.infras.resources.base.kres import KPod
from paas_wl.infras.resources.kube_res.base import Schedule
from paas_wl.utils.constants import PodPhase
from paas_wl.workloads.release_controller.constants import ImagePullPolicy

logger = logging.getLogger(__name__)


@define
class SecurityContext:
    privileged: bool = True


@dataclass
class ContainerRuntimeSpec:
    """Container runtime specifications"""

    image: str
    envs: Dict[str, str] = field(default_factory=dict)
    securityContext: SecurityContext = field(default_factory=SecurityContext)
    image_pull_policy: ImagePullPolicy = field(default=ImagePullPolicy.IF_NOT_PRESENT)
    image_pull_secrets: List[Dict[str, str]] = field(default_factory=list)
    # The resources required by the container
    # e.g. {"limits": {"cpu": "1", "memory": "1Gi"}, "requests": {"cpu": "1", "memory": "1Gi"}}
    resources: Dict[str, Dict[str, str]] = field(default_factory=dict)


@dataclass
class SmartBuilderTemplate:
    """S-Mart Builder Pod Template"""

    name: str
    namespace: str
    runtime: ContainerRuntimeSpec
    schedule: Schedule


class SmartBuildHandler(PodScheduleHandler):
    """S-Mart Builder Handler"""

    def build_pod(self, template: SmartBuilderTemplate) -> str:
        """Create build Pod

        :param template: the template to run builder
        :return: Pod name
        """

        pod_name = self.normalize_builder_name(template.name)
        try:
            smart_builder_pod = KPod(self.client).get(pod_name, namespace=template.namespace)
        except ResourceMissing:
            logger.info(
                "build smart builder pod <%s/%s> does not exist, will create one", template.namespace, template.name
            )
        else:
            if smart_builder_pod.status.phase == PodPhase.RUNNING:
                # 重复构建时, 上一次构建 pod 执行超时将尝试删除并重新构建, 否则取消本次构建
                if not self.check_pod_timeout(smart_builder_pod):
                    raise ResourceDuplicate(
                        "Pod", pod_name, extra_value=self.get_pod_timeout(smart_builder_pod).humanize(locale="zh")
                    )

                logger.info(
                    "Pod %s timed out after %s seconds, recreating", pod_name, settings.MAX_SMART_BUILDER_SECONDS
                )
            else:
                logger.debug("Pod %s is not running, deleting", pod_name)

            self.delete_builder(template.namespace, pod_name, force=True)

        pod_body = self._construct_pod_body(pod_name, template)
        pod_info, _ = KPod(self.client).create_or_update(pod_name, template.namespace, body=pod_body)
        return pod_info.metadata.name

    def delete_builder(self, namespace: str, name: str, force: bool = False):
        """Deleting the builder Pod"""

        pod_name = self.normalize_builder_name(name)
        return self._delete_finished_pod(namespace, pod_name, force=force)

    def wait_for_succeeded(self, namespace: str, name: str, timeout: float | None = None, check_period: float = 0.5):
        """Wait for the Pod to complete successfully"""

        pod_name = self.normalize_builder_name(name)
        return self._wait_pod_succeeded(namespace, pod_name, timeout=timeout, check_period=check_period)

    def wait_for_logs_readiness(self, namespace: str, name: str, timeout: int):
        """Wait for Pod logs readiness"""

        pod_name = self.normalize_builder_name(name)
        log_available_statuses = {PodPhase.RUNNING, PodPhase.SUCCEEDED, PodPhase.FAILED}
        KPod(self.client).wait_for_status(pod_name, log_available_statuses, namespace, timeout)

    def get_build_log(self, namespace: str, name: str, timeout: int, **kwargs):
        """Get build log"""

        pod_name = self.normalize_builder_name(name)
        return super()._get_pod_logs(namespace, pod_name, timeout=timeout, **kwargs)

    def _construct_pod_body(self, pod_name: str, template: SmartBuilderTemplate) -> Dict[str, Any]:
        """Constructing Pod Configuration"""

        env_list = []
        for key, value in template.runtime.envs.items():
            env_list.append(dict(name=str(key), value=str(value)))

        pod_body: Dict = {
            "metadata": {
                "name": pod_name,
                "namespace": template.namespace,
                "labels": {"pod_selector": pod_name, "category": "smart-app-builder"},
            },
            "spec": {
                "containers": [
                    {
                        "env": env_list,
                        "image": template.runtime.image,
                        "name": pod_name,
                        "imagePullPolicy": template.runtime.image_pull_policy.value,
                        "resources": template.runtime.resources,
                        "securityContext": {"privileged": template.runtime.securityContext.privileged},
                    },
                ],
                "restartPolicy": "Never",
                "nodeSelector": template.schedule.node_selector,
                "imagePullSecrets": template.runtime.image_pull_secrets,
            },
            "apiVersion": "v1",
            "kind": "Pod",
        }

        if template.schedule.tolerations:
            pod_body["spec"]["tolerations"] = template.schedule.tolerations

        return pod_body

    @staticmethod
    def normalize_builder_name(name: str) -> str:
        """Normalize builder names"""

        # TODO: 暂时直接返回 name, 后面需要添加对 name 的校验
        return name
