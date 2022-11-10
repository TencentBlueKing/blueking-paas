import json
from typing import List, Optional

import kubernetes.client.models as kmodels
from attrs import define
from blue_krill.data_types.enum import StructuredEnum
from blue_krill.text import remove_prefix
from kubernetes.client import ApiClient
from kubernetes.dynamic.resource import ResourceInstance


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
        self.data = json.dumps(instance.to_dict())


def parse_pod(instance: ResourceInstance) -> kmodels.V1Pod:
    """parse a dynamic instance to V1Pod
    :raise: ValueError if instance is an invalid V1Pod
    """
    return ApiClient().deserialize(FakeResponse(instance), kmodels.V1Pod)


def check_pod_health_status(pod: kmodels.V1Pod) -> HealthStatus:
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
            return unhealthy.with_message(fail_message)
        return progressing
    else:
        return HealthStatus(
            reason=pod_status.phase or "unknown", message=pod_status.message, status=HealthStatusType.UNKNOWN
        )


def get_any_container_fail_message(pod: kmodels.V1Pod) -> Optional[str]:
    """获取 Pod 其中一个容器的失败信息"""
    for ctr in pod.status.container_statuses or []:
        if fail_message := get_container_fail_message(ctr):
            return fail_message
    return None


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
