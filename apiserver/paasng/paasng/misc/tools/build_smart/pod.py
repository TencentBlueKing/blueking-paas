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

import datetime
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List

import arrow
from attrs import define
from django.conf import settings
from django.utils.timezone import localtime

from paas_wl.infras.resources.base.base import get_client_by_cluster_name
from paas_wl.infras.resources.base.exceptions import ReadTargetStatusTimeout, ResourceDuplicate, ResourceMissing
from paas_wl.infras.resources.base.kres import KPod
from paas_wl.infras.resources.kube_res.base import Schedule
from paas_wl.utils.constants import PodPhase
from paas_wl.workloads.release_controller.constants import ImagePullPolicy

from .models import SmartBuildRecord
from .output import StreamType, get_default_stream

logger = logging.getLogger(__name__)


@define
class SecurityContext:
    privileged: bool = True


@dataclass
class Containers:
    """The runtime specification of a container which contains image and other info."""

    image: str
    envs: Dict[str, str] = field(default_factory=dict)
    securityContext: SecurityContext = field(default_factory=SecurityContext)


@dataclass
class SmartBuildSpec:
    """The template to run the smart-app-builder Pod

    :param containers: Container Info of the Pod, including image, securityContext and so on.
    :param schedule: Schedule Rule of the Pod, including tolerations and node_selector.
    :param name: the name of the Pod
    :param namespace: the namespace of the Pod
    """

    containers: Containers
    schedule: Schedule
    name: str = field(default="builder")
    namespace: str = field(default="smart-app-builder")


class SmartBuildRunner:
    """Responsible for starting the s-mart package building task in k8s

    This class creates a Pod to execute the build,
    and monitors its status and log output in real time.

    :param build_id: build task ID, used for logging and identification
    :param spec: s-mart build specification
    :param timeout: build timeout (in seconds)
    :param poll_interval: polling interval (in seconds)
    """

    def __init__(
        self,
        smart_build: SmartBuildRecord,
        spec: SmartBuildSpec,
        timeout: int = 1800,
        poll_interval: float = 2.0,
    ):
        self.smart_build = smart_build
        self.spec = spec
        self.timeout = timeout
        self.poll_interval = poll_interval

        self.client = get_client_by_cluster_name(cluster_name=self.spec.schedule.cluster_name)
        self.writer = get_default_stream(smart_build)

    def start(self) -> PodPhase:
        """Start a Pod for building the s-mart package

        Create and monitor the build pod,
        processing logs and status changes until the build completes or times out.
        Finally, clean up resources and update the build log.
        """

        spec = self.spec
        pod_name = self.spec.name
        try:
            smart_builder_pod = KPod(self.client).get(name=pod_name, namespace=spec.namespace)
        except ResourceMissing:
            logger.info(f"Pod {spec.namespace}/{pod_name} does not exist, creating a new one")
        else:
            if smart_builder_pod.status.phase == PodPhase.RUNNING:
                if not self.check_pod_timeout(smart_builder_pod):
                    raise ResourceDuplicate(
                        resource="Pod",
                        resource_name=pod_name,
                        extra_value=self.get_pod_timeout(smart_builder_pod).humanize(locale="zh"),
                    )
                logger.info(
                    "%s has running more than %s, delete it and re-create one",
                    pod_name,
                    settings.MAX_SMART_BUILDER_SECONDS,
                )

            self._delete_pod(namespace=spec.namespace, pod_name=pod_name)
            logger.info("Deleted Pod %s/%s", spec.namespace, pod_name)

        env_list: List[Dict[str, str]] = []
        for key, value in spec.containers.envs.items():
            env_list.append(dict(name=key, value=value))

        smart_builder_pod_body: Dict[str, Any] = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": pod_name,
                "namespace": spec.namespace,
            },
            "spec": {
                "containers": [
                    {
                        "env": env_list,
                        "image": spec.containers.image,
                        "name": pod_name,
                        "imagePullPolicy": ImagePullPolicy.ALWAYS,
                        "securityContext": {"privileged": spec.containers.securityContext.privileged},
                    },
                ],
                "restartPolicy": "Never",
            },
        }

        if spec.schedule.tolerations:
            smart_builder_pod_body["spec"]["tolerations"] = spec.schedule.tolerations

        pod_info, _ = KPod(self.client).create_or_update(
            name=pod_name, namespace=spec.namespace, body=smart_builder_pod_body
        )

        logger.info(f"Pod {spec.namespace}/{pod_name} created successfully, starting build process...")

        result_status = PodPhase.RUNNING
        try:
            # Start monitoring Pod status
            result_status = self._monitor_pod_status(pod_info)
        except Exception as e:
            logger.exception("Error during s-mart build")
            self.writer.write_message(
                f"Build failed with error: {str(e)}",
                stream=StreamType.STDERR.value,
            )
            result_status = PodPhase.FAILED
        finally:
            # clean up pod resources
            self._delete_pod(namespace=spec.namespace, pod_name=pod_name)

        return result_status

    def _read_log_increment(self, sent_len: int, name: str, namespace: str) -> int:
        """Read and output the incremental portion of a Pod log

        :param sent_len: Length of the read log
        :returns: Total length of the new log
        """
        try:
            stream = KPod(self.client).get_log(name=name, namespace=namespace, timeout=8)
            raw = stream.read().decode(errors="ignore")
        except Exception as e:
            logger.debug("fetch build logs failed: %s", e)
            return sent_len

        if len(raw) <= sent_len:
            return sent_len

        # Process new logs
        for line in raw[sent_len:].rstrip().splitlines():
            if line.strip():
                self.writer.write_message(line)

        return len(raw)

    def _monitor_pod_status(self, pod_info) -> PodPhase:
        """Monitors the Pod status until it completes or times out.

        :returns: Final Pod status.
        """
        pod_name = pod_info.metadata.name
        pod_namespace = pod_info.metadata.namespace

        start_ts = time.time()
        deadline = start_ts + self.timeout
        sent_len = 0
        poll = max(self.poll_interval, 0.5)

        # target statuses are strings expected by KPod.wait_for_status
        target_statuses = {PodPhase.SUCCEEDED.value, PodPhase.FAILED.value}

        while True:
            # Check global timeout
            now = time.time()
            if now >= deadline:
                self.writer.write_message(
                    f"Build timeout: {int(now - start_ts)} seconds", stream=StreamType.STDERR.value
                )
                return PodPhase.FAILED

            # Try waiting a short chunk for final status;
            # if timeout occurs, ReadTargetStatusTimeout is raised
            chunk = min(poll, deadline - now)
            try:
                # wait_for_status will return the phase string when one of target_statuses is reached
                phase_str = KPod(self.client).wait_for_status(
                    pod_name,
                    target_statuses=target_statuses,
                    namespace=pod_namespace,
                    timeout=chunk,
                    check_period=poll,
                )
            except ReadTargetStatusTimeout:
                # not finished in this chunk -> read incremental logs and continue
                sent_len = self._read_log_increment(sent_len, pod_name, pod_namespace)
                continue
            else:
                # reached final phase, ensure final logs are flushed
                sent_len = self._read_log_increment(sent_len, pod_name, pod_namespace)
                try:
                    return PodPhase(phase_str)
                except Exception:
                    logger.debug("Unknown pod phase returned: %s", phase_str)
                    return PodPhase.FAILED

    def _delete_pod(self, namespace: str, pod_name: str):
        """Delete Pod directly, Don't check status at first."""
        logger.debug(f"trying to clean slug pod<{pod_name}>.")
        try:
            KPod(self.client).delete(pod_name, namespace=namespace)
            self.writer.write_message(f"Pod {namespace}/{pod_name} deleted successfully")
        except Exception as e:
            logger.debug("delete pod failed: %s", e)
            self.writer.write_message(
                f"Failed to delete Pod {namespace}/{pod_name}: {e}",
                stream=StreamType.STDERR.value,
            )

    def check_pod_timeout(self, pod_info) -> bool:
        """Check A Pod whether running too long"""
        now = arrow.get(localtime())
        when_timeout = self.get_pod_timeout(pod_info)
        return when_timeout <= now

    @staticmethod
    def get_pod_timeout(pod_info) -> arrow.Arrow:
        return arrow.get(pod_info.status.startTime) + datetime.timedelta(seconds=settings.MAX_SMART_BUILDER_SECONDS)
