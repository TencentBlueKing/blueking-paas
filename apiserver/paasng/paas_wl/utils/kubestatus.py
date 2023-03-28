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
import json
from typing import List, Optional, Type, TypeVar, Union

import kubernetes.client.models as kmodels
from attrs import define
from blue_krill.data_types.enum import StructuredEnum
from blue_krill.text import remove_prefix
from kubernetes.client import ApiClient
from kubernetes.dynamic.resource import ResourceField, ResourceInstance


class HealthStatusType(StructuredEnum):
    HEALTHY = "Healthy"
    UNHEALTHY = "Unhealthy"
    PROGRESSING = "progressing"
    UNKNOWN = "Unknown"


@define
class HealthStatus:
    """the resource health status"""

    reason: str
    message: str
    status: HealthStatusType

    def with_message(self, message) -> 'HealthStatus':
        self.message = message
        return self


class FakeResponse:
    def __init__(self, instance):
        self.data = json.dumps(self.__serialize(instance))

    @classmethod
    def __serialize(cls, field):
        if isinstance(field, ResourceField):
            return {k: cls.__serialize(v) for k, v in field.__dict__.items()}
        elif isinstance(field, (list, tuple)):
            return [cls.__serialize(item) for item in field]
        elif isinstance(field, ResourceInstance):
            return field.to_dict()
        else:
            return field


T = TypeVar("T")


def parse_dynamic_instance(instance: Union[ResourceInstance, ResourceField], type_: Type[T]) -> T:
    """parse a dynamic instance to T
    :raise: ValueError if instance is an invalid T
    """
    return ApiClient().deserialize(FakeResponse(instance), type_)


def parse_pod(instance: Union[ResourceInstance, ResourceField]) -> kmodels.V1Pod:
    """parse a dynamic instance to V1Pod
    :raise: ValueError if instance is an invalid V1Pod
    """
    return parse_dynamic_instance(instance, kmodels.V1Pod)


def parse_container_status(instance: Union[ResourceInstance, ResourceField]) -> kmodels.V1ContainerStatus:
    """parse a dynamic instance to V1Pod
    :raise: ValueError if instance is an invalid V1Pod
    """
    return parse_dynamic_instance(instance, kmodels.V1ContainerStatus)


def check_pod_health_status(pod: kmodels.V1Pod) -> HealthStatus:  # noqa: C901
    """check if the pod is healthy
    For a Pod, healthy is meaning that the Pod is successfully complete or is Ready
               unhealthy is meaning that the Pod is restarting or is Failed
               progressing is meaning that the Pod is still running and condition `PodReady` is False.
    """

    pod_status: kmodels.V1PodStatus = pod.status
    healthy = HealthStatus(reason=pod_status.reason, message=pod_status.message, status=HealthStatusType.HEALTHY)
    unhealthy = HealthStatus(reason=pod_status.reason, message=pod_status.message, status=HealthStatusType.UNHEALTHY)
    progressing = HealthStatus(
        reason=pod_status.reason, message=pod_status.message, status=HealthStatusType.PROGRESSING
    )
    if pod_status.phase == "Succeeded":
        return healthy
    elif pod_status.phase == "Running":
        pod_spec: kmodels.V1PodSpec = pod.spec
        if pod_spec.restart_policy == "Always":
            # Ready means the pod is able to service requests
            # and should be added to the load balancing pools of all matching services.
            cond_ready = find_pod_status_condition(pod_status.conditions or [], cond_type="Ready")
            if cond_ready and cond_ready.status == "True":
                return healthy
            if fail_message := get_any_container_fail_message(pod):
                return unhealthy.with_message(fail_message)
            return progressing
        return progressing
    elif pod_status.phase == "Failed":
        if pod_status.message:
            return unhealthy
        if fail_message := get_any_container_fail_message(pod):
            return unhealthy.with_message(fail_message)
        return unhealthy.with_message("unknown")
    elif pod_status.phase == "Pending":
        if fail_message := get_any_container_fail_message(pod):
            # ContainerCreating: 无 init containers 的 Pod 的默认状态
            # PodInitializing: 有 init containers 的 Pod 的默认状态
            # 处于这两个状态的 Pod 仍然在 Pending
            if fail_message not in ["ContainerCreating", "PodInitializing"]:
                return unhealthy.with_message(fail_message)
        # PodScheduled represents status of the scheduling process for this pod.
        scheduled_cond = find_pod_status_condition(pod_status.conditions or [], cond_type="PodScheduled")
        if scheduled_cond and scheduled_cond.status == "False":
            # PodScheduled will be False for many reason, something should be regarded as Failed
            # - Unschedulable means that the scheduler can't schedule the pod right now,
            # for example due to insufficient resources in the cluster.
            # - SchedulingGated means that the scheduler skips scheduling the pod
            # because one or more scheduling gates are still present.
            if scheduled_cond.reason in ["Unschedulable", "SchedulingGated"]:
                return unhealthy.with_message(scheduled_cond.message)
            # otherwise, the pod is still scheduling
        return progressing
    else:
        return HealthStatus(
            reason=pod_status.phase or "unknown", message=pod_status.message, status=HealthStatusType.UNKNOWN
        )


def get_any_container_fail_message(pod: kmodels.V1Pod) -> str:
    """获取 Pod 其中一个容器的失败信息"""
    for ctr in pod.status.container_statuses or []:
        if fail_message := get_container_fail_message(ctr):
            return fail_message
    return f"container is not in terminated or waiting state and pod.status.phase is {pod.status.phase}"


def get_container_fail_message(ctr: kmodels.V1ContainerStatus) -> Optional[str]:
    """获取容器的失败信息"""
    if fail_message := get_container_failed_message_from_state(ctr.state):
        return fail_message
    if fail_message := get_container_failed_message_from_state(ctr.last_state):
        return fail_message
    return None


def get_container_failed_message_from_state(state: kmodels.V1ContainerState) -> Optional[str]:
    """获取容器的失败信息(核心实现)"""
    if state.terminated:
        terminated: kmodels.V1ContainerStateTerminated = state.terminated
        if terminated.message:
            return terminated.message
        if terminated.reason == "OOMKilled":
            return "OOMKilled"
        if terminated.exit_code != 0:
            return f"failed with exit code {terminated.exit_code}"
    if state.waiting:
        waiting: kmodels.V1ContainerStateWaiting = state.waiting
        if waiting.message:
            return waiting.message
        return waiting.reason
    return None


def find_pod_status_condition(
    conditions: List[kmodels.V1PodCondition], cond_type: str
) -> Optional[kmodels.V1PodCondition]:
    """finds the conditionType in conditions."""
    for cond in conditions:
        if cond.type == cond_type:
            return cond
    return None


def extract_exit_code(health_status: HealthStatus) -> Optional[int]:
    """A helper to extract exit code"""
    try:
        return int(remove_prefix(health_status.message, "failed with exit code "))
    except ValueError:
        return None
