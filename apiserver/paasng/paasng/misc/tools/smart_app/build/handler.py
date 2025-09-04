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
from typing import Any, Dict, List, Optional

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
    """The runtime specification of a container which contains image and other info."""

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
    """The template to run the smart-app-builder Pod

    :param name: the name of the Pod
    :param namespace: the namespace of the Pod
    :param containers: Container Info of the Pod, including image, securityContext and so on.
    :param schedule: Schedule Rule of the Pod, including tolerations and node_selector.
    """

    name: str
    namespace: str
    runtime: ContainerRuntimeSpec
    schedule: Schedule


class SmartBuildHandler(PodScheduleHandler):
    """Handler for s-mart app builder pod."""

    def build_pod(self, template: SmartBuilderTemplate) -> str:
        """Start a Pod for Build s-mart package

        :param template: the template to run builder
        :returns: The name of smart build pod
        """
        pod_name = self.normalize_builder_name(template.name)
        try:
            smart_builder_pod = KPod(self.client).get(pod_name, namespace=template.namespace)
        except ResourceMissing:
            logger.info(
                "build smart builder <%s/%s> does not exist, will create one", template.namespace, template.name
            )
        else:
            # ignore the other pods
            if smart_builder_pod.status.phase == PodPhase.RUNNING:
                # 重复构建时 上一次构建 pod 执行超时将尝试删除并重新构建, 否则取消本次构建
                if not self.check_pod_timeout(smart_builder_pod):
                    raise ResourceDuplicate(
                        "Pod", pod_name, extra_value=self.get_pod_timeout(smart_builder_pod).humanize(locale="zh")
                    )

                logger.info(
                    "%s has been running more than %s seconds, delete it and re-create one",
                    pod_name,
                    settings.MAX_SMART_BUILDER_SECONDS,
                )

                self._delete_pod(namespace=template.namespace, pod_name=pod_name, grace_period_seconds=0).wait()

        smart_builder_pod_body = self._construct_pod_body(pod_name, template)

        pod_info, _ = KPod(self.client).create_or_update(
            name=pod_name, namespace=template.namespace, body=smart_builder_pod_body
        )
        return pod_info.metadata.name

    def delete_builder(self, namespace: str, name: str):
        """Force delete a slug builder pod unless it's in "running" phase."""
        pod_name = self.normalize_builder_name(name)
        return self._delete_finished_pod(namespace=namespace, pod_name=pod_name, force=False)

    def wait_for_succeeded(
        self, namespace: str, name: str, timeout: Optional[float] = None, check_period: float = 0.5
    ):
        """Calling this function will blocks until the pod's status has become Succeeded

        :param name: the builder pod name
        :param timeout: maximum time to wait in seconds, or None to wait indefinitely
        :param check_period: time to wait between each status check
        :raises: PodNotSucceededError when Pod does not succeed in given timeout seconds
        """
        pod_name = self.normalize_builder_name(name)
        return self._wait_pod_succeeded(
            namespace=namespace, pod_name=pod_name, timeout=timeout, check_period=check_period
        )

    def wait_for_logs_readiness(self, namespace: str, name: str, timeout: int):
        """Waits for slugbuilder Pod to become ready for retrieving logs

        :param name: the builder pod name
        :param timeout: max timeout
        """
        pod_name = self.normalize_builder_name(name)
        log_available_statuses = {PodPhase.RUNNING, PodPhase.SUCCEEDED, PodPhase.FAILED}
        KPod(self.client).wait_for_status(
            name=pod_name, namespace=namespace, target_statuses=log_available_statuses, timeout=timeout
        )

    def get_build_log(self, namespace: str, name: str, timeout: int, **kwargs):
        """Get logs of building process

        :param name: the builder pod name
        """
        pod_name = self.normalize_builder_name(name)
        return super()._get_pod_logs(namespace=namespace, pod_name=pod_name, timeout=timeout, **kwargs)

    def _construct_pod_body(self, pod_name: str, template: SmartBuilderTemplate) -> Dict[str, Any]:
        """Construct the pod body for smart builder pod"""
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
        """Get A k8s friendly pod name.

        Although we return as is now, we reserve the ability to normalize/modify this name

        :param name: builder name of engine app
        """
        return name
