# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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
import os
import time
from enum import StrEnum
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

import arrow
from django.conf import settings
from django.utils.timezone import localtime
from kubernetes.client.rest import ApiException

from paas_wl.bk_app.monitoring.app_monitor.utils import build_monitor_port
from paas_wl.bk_app.processes.kres_entities import Process
from paas_wl.infras.resources.base.exceptions import (
    CreateServiceAccountTimeout,
    PodAbsentError,
    PodNotSucceededError,
    PodTimeoutError,
    ResourceDeleteTimeout,
    ResourceDuplicate,
    ResourceMissing,
)
from paas_wl.infras.resources.base.kres import KDeployment, KNamespace, KPod, KReplicaSet, set_default_options
from paas_wl.infras.resources.generation.mapper import MapperProcConfig, ResourceIdentifiers
from paas_wl.infras.resources.generation.version import AppResVerManager
from paas_wl.infras.resources.kube_res.base import AppEntityManager
from paas_wl.infras.resources.kube_res.exceptions import AppEntityNotFound
from paas_wl.infras.resources.utils.basic import get_client_by_app
from paas_wl.utils.constants import PodPhase
from paas_wl.utils.kubestatus import (
    HealthStatus,
    HealthStatusType,
    check_pod_health_status,
    extract_exit_code,
    parse_pod,
)
from paas_wl.workloads.autoscaling.kres_entities import ProcAutoscaling
from paas_wl.workloads.images.kres_entities import ImageCredentials, credentials_kmodel
from paas_wl.workloads.networking.ingress.managers.service import ProcDefaultServices
from paas_wl.workloads.release_controller.hooks.kres_entities import Command, command_kmodel

if TYPE_CHECKING:
    import kubernetes.client.models as km

    from paas_wl.bk_app.applications.models import WlApp
    from paas_wl.infras.resources.base.base import EnhancedApiClient
    from paasng.platform.engine.configurations.building import SlugBuilderTemplate

logger = logging.getLogger(__name__)


class BuildProbeStatus(StrEnum):
    """构建探针检测状态, 用于 check_probe_and_pod 返回值."""

    POD_ENDED = "pod_ended"
    BUILDING = "building"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


# Probe polling interval in seconds for build debug mode
_PROBE_POLL_INTERVAL = 5

# Label key/value for build-debug pods
BUILD_DEBUG_LABEL_KEY = "build-debug"
BUILD_DEBUG_LABEL_VALUE = "true"


class BuildProbePoller:
    """轮询 Pod 探针状态直到构建完成.

    封装了超时兜底、时序误判重检等逻辑，将轮询职责从 DefaultBuildProcessExecutor 中分离。
    ResourceMissing 被视为 Pod 已结束，返回 None。
    """

    def __init__(self, handler: "BuildHandler", namespace: str, name: str):
        self.handler = handler
        self.namespace = namespace
        self.name = name

    def poll_until_ready(self) -> BuildProbeStatus | None:
        """轮询直到构建完成或超时.

        :returns: BuildProbeStatus 或 None (超时 / Pod 已结束 / ResourceMissing)
        """
        deadline = time.monotonic() + settings.BUILD_PROCESS_TIMEOUT

        while time.monotonic() < deadline:
            time.sleep(_PROBE_POLL_INTERVAL)

            try:
                status = self.handler.check_probe_and_pod(self.namespace, self.name)
            except ResourceMissing:
                logger.info("Builder Pod<%s/%s> not found, treating as ended.", self.namespace, self.name)
                return None
            except ValueError:
                logger.exception("Failed to parse pod status for Pod<%s/%s>, retrying.", self.namespace, self.name)
                continue

            if status == BuildProbeStatus.POD_ENDED:
                logger.info("Builder Pod<%s/%s> has ended, exiting log stream.", self.namespace, self.name)
                return None

            if status == BuildProbeStatus.SUCCEEDED:
                return BuildProbeStatus.SUCCEEDED

            if status == BuildProbeStatus.FAILED:
                # started=True but ready=False: 等待一个探针周期后重检, 消除时序误判
                logger.info(
                    "Builder Pod<%s/%s> startup probe passed but readiness not ready, waiting one probe cycle.",
                    self.namespace,
                    self.name,
                )
                time.sleep(_PROBE_POLL_INTERVAL)
                try:
                    retry_status = self.handler.check_probe_and_pod(self.namespace, self.name)
                except (ResourceMissing, ValueError):
                    return BuildProbeStatus.FAILED
                return retry_status if retry_status == BuildProbeStatus.SUCCEEDED else BuildProbeStatus.FAILED

            # BUILDING: 继续轮询

        logger.warning(
            "Builder Pod<%s/%s> probe polling timed out after %s seconds.",
            self.namespace,
            self.name,
            settings.BUILD_PROCESS_TIMEOUT,
        )
        return None


# Set the default timeout
set_default_options({"request_timeout": (settings.K8S_DEFAULT_CONNECT_TIMEOUT, settings.K8S_DEFAULT_READ_TIMEOUT)})


def ensure_image_credentials_secret(app: "WlApp"):
    """确保应用镜像的访问凭证存在。"""
    credentials = ImageCredentials.load_from_app(app)
    credentials_kmodel.upsert(credentials, update_method="patch")


class ResourceHandlerBase:
    """The base class for handling resources."""

    def __init__(self, client: "EnhancedApiClient"):
        self.client = client

    @classmethod
    def new_by_app(cls, app: "WlApp"):
        """Create a handler object by app object."""
        client = get_client_by_app(app)
        return cls(client)


class ProcessesHandler(ResourceHandlerBase):
    """Process handler."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.process_manager: AppEntityManager[Process, "WlApp"] = AppEntityManager(Process)

    def deploy(self, processes: List[Process]):
        """Deploy a list process objects.

        :param processes: The process list.
        """
        for process in processes:
            mapper_ver = AppResVerManager(process.app).curr_version
            try:
                self.process_manager.update(process, "replace", mapper_version=mapper_ver, allow_not_concrete=True)
            except AppEntityNotFound:
                self.process_manager.create(process, mapper_version=mapper_ver)
            self.get_default_services(process.app, process.type).create_or_patch()

    def shutdown(self, config: MapperProcConfig):
        """Shutdown a process.

        :param config: The mapper proc config object.
        """
        self.scale(config, 0)

    def scale(self, config: MapperProcConfig, replicas: int):
        """Scale a process's replicas to given value.

        :param config: The mapper proc config object.
        :param replicas: The replicas value, such as 2.
        """
        self.get_default_services(config.app, config.type).create_or_patch()

        # Send patch request
        patch_body = {"spec": {"replicas": replicas}}
        KDeployment(self.client).patch(
            self.res_identifiers(config).deployment_name, namespace=config.app.namespace, body=patch_body
        )

    def delete(self, config: MapperProcConfig, remove_svc: bool):
        """Delete a process by the config object.

        :param config: The mapper proc config object.
        :param remove_svc: Whether to remove the related default service.
        """
        app = config.app
        if remove_svc:
            self.get_default_services(app, config.type).remove()

        # Delete the resources
        res = self.res_identifiers(config)
        KDeployment(self.client).delete(res.deployment_name, namespace=app.namespace, non_grace_period=True)
        # Delete ReplicaSet and Pods manually
        KReplicaSet(self.client).ops_batch.delete_collection(labels=res.match_labels, namespace=app.namespace)
        KPod(self.client).ops_batch.delete_individual(labels=res.match_labels, namespace=app.namespace)

    def delete_gracefully(self, config: MapperProcConfig):
        """Delete a process gracefully by the config object.

        :param config: The mapper proc config object.
        """
        res = self.res_identifiers(config)
        KDeployment(self.client).delete(res.deployment_name, namespace=config.app.namespace)

    @staticmethod
    def res_identifiers(config: MapperProcConfig) -> ResourceIdentifiers:
        """Get the resource identifiers of a process."""
        mapper_version = AppResVerManager(config.app).curr_version
        return mapper_version.proc_resources(config)

    @staticmethod
    def get_default_services(app: "WlApp", process_type: str) -> ProcDefaultServices:
        monitor_port = build_monitor_port(app)
        return ProcDefaultServices(app, process_type, monitor_port=monitor_port)


class NamespacesHandler(ResourceHandlerBase):
    """Handler for namespace resources"""

    def ensure_namespace(self, namespace: str, max_wait_seconds: int = 15):
        """确保命名空间存在, 如果命名空间不存在, 那么将创建一个 Namespace 和 ServiceAccount

        :param namespace: 需要确保存在的 namespace
        :param max_wait_seconds: 等待 ServiceAccount 就绪的时间
        """
        self.create(namespace)
        self.check_service_account_secret(namespace, max_wait_seconds=max_wait_seconds)

    def delete(self, namespace: str):
        """k8s 直接删除 namespace 将清除其下所有资源"""
        KNamespace(self.client).delete(namespace)

    def create(self, namespace: str):
        """
        :return: instance of namespace, created
        """
        return KNamespace(self.client).get_or_create(namespace)

    def check_service_account_secret(self, namespace: str, max_wait_seconds=15):
        try:
            KNamespace(self.client).wait_for_default_sa(namespace, timeout=max_wait_seconds)
        except CreateServiceAccountTimeout:
            logger.exception("timeout while waiting for the default sa of %s to be created", namespace)
            raise


class WaitPodDelete:
    _check_interval = 1

    def __init__(self, namespace: str, name: str, client: "EnhancedApiClient"):
        self.namespace = namespace
        self.name = name
        self.client = client

    def wait(self, max_wait_seconds: int = 60, raise_timeout: bool = False) -> bool:
        """Wait for the pod to actually be deleted from the server.

        :param max_wait_seconds: the max wait time.
        :param raise_timeout: whether to throw an exception when timeout.
        :return: whether actually be deleted, `true` for be deleted.
        """
        now = datetime.datetime.now()
        when_timeout = now + datetime.timedelta(seconds=max_wait_seconds)
        while now <= when_timeout:
            time.sleep(self._check_interval)
            now = datetime.datetime.now()
            try:
                KPod(self.client).get(name=self.name, namespace=self.namespace)
            except ResourceMissing:
                return True
        if raise_timeout:
            raise ResourceDeleteTimeout(resource_type="pod", namespace=self.namespace, name=self.name)
        return False


class PodScheduleHandler(ResourceHandlerBase):
    """PodScheduleHandler 提供了操作 Pod 的公共方法."""

    def _get_pod_status(self, namespace: str, pod_name: str) -> Tuple[str, HealthStatus]:
        """
        :raise: ResourceMissing if pod not found
        """
        pod = KPod(self.client).get(pod_name, namespace=namespace)
        health_status = check_pod_health_status(parse_pod(pod))
        return pod.status.phase, health_status

    def _delete_finished_pod(
        self, namespace: str, pod_name: str, force: bool = True, raise_if_non_exists: bool = False
    ):
        """Generic Pod Delete Action

        :param namespace: 应用命名空间
        :param pod_name: Pod name
        :param force: 如果 Pod 正在运行, 是否强制删除?
        """
        try:
            pod = KPod(self.client).get(pod_name, namespace=namespace)
        except ResourceMissing:
            logger.info(f"Pod<{namespace}/{pod_name}> does not exist, maybe have been cleaned.")
            if raise_if_non_exists:
                raise
        else:
            # ignore the other pods
            if pod.status.phase == PodPhase.RUNNING and not force:
                logger.warning(f"trying to clean Pod<{namespace}/{pod_name}>, but it's still running.")
                return None

            logger.debug(f"trying to clean pod<{namespace}/{pod_name}>.")
            # no matter the pod is completed or crash
            KPod(self.client).delete(
                pod_name, namespace=namespace, non_grace_period=True, raise_if_non_exists=raise_if_non_exists
            )
            return WaitPodDelete(namespace=namespace, name=pod_name, client=self.client)

    def _delete_pod(
        self, namespace: str, pod_name: str, grace_period_seconds: int = 1, raise_if_non_exists: bool = False
    ):
        """Delete Pod directly, Don't check status at first."""
        logger.debug(f"trying to clean slug pod<{pod_name}>.")
        # no matter the pod is completed or crash
        KPod(self.client).delete(
            pod_name,
            namespace=namespace,
            non_grace_period=grace_period_seconds == 0,
            raise_if_non_exists=raise_if_non_exists,
            grace_period_seconds=grace_period_seconds,
        )
        return WaitPodDelete(namespace=namespace, name=pod_name, client=self.client)

    def _wait_pod_succeeded(
        self, namespace: str, pod_name: str, timeout: Optional[float] = None, check_period: float = 0.5
    ):
        """Calling this function will block until the pod's status has become Succeeded

        :param namespace: 应用命名空间
        :param pod_name: Pod name
        :raises: PodAbsentError when Pod is not found
        :raises: PodTimeoutError when Pod does not succeed in given timeout seconds
        """
        time_started = time.time()
        while timeout is None or time.time() - time_started < timeout:
            try:
                _, health_status = self._get_pod_status(namespace, pod_name)
            except ResourceMissing as e:
                raise PodAbsentError(f"Pod<{namespace}/{pod_name}> not found") from e

            if health_status.status == HealthStatusType.UNHEALTHY:
                exit_code = extract_exit_code(health_status) or -1
                raise PodNotSucceededError(
                    f"Pod<{namespace}/{pod_name}> ends unsuccessfully",
                    reason=health_status.reason,
                    message=health_status.message,
                    exit_code=exit_code,
                )
            elif health_status.status == HealthStatusType.HEALTHY:
                return True
            else:
                time.sleep(check_period)
                continue
        raise PodTimeoutError(f"Pod<{namespace}/{pod_name}> didn't succeeded in {timeout} seconds.")

    def _get_pod_logs(self, namespace: str, pod_name: str, timeout: int, **kwargs):
        """Get logs of running pod.

        :param namespace: 应用命名空间
        :param pod_name: Pod name
        """
        return KPod(self.client).get_log(name=pod_name, namespace=namespace, timeout=timeout, **kwargs)

    def check_pod_timeout(self, pod_info) -> bool:
        """Check A Pod whether running too long"""
        now = arrow.get(localtime())
        when_timeout = self.get_pod_timeout(pod_info)
        return when_timeout <= now

    @staticmethod
    def get_pod_timeout(pod_info) -> arrow.Arrow:
        return arrow.get(pod_info.status.startTime) + datetime.timedelta(seconds=settings.MAX_SLUG_SECONDS)


class BuildHandler(PodScheduleHandler):
    """Handler for slugbuilder pod."""

    def build_slug(self, template: "SlugBuilderTemplate") -> str:
        """Start a Pod for building slug

        :param template: the template to run builder
        :returns: The name of slug build pod
        """
        pod_name = self.normalize_builder_name(template.name)
        try:
            slug_pod = KPod(self.client).get(pod_name, namespace=template.namespace)
        except ResourceMissing:
            logger.info("build slug<%s/%s> does not exist, will create one", template.namespace, template.name)
        else:
            # 构建调试模式: 旧 debug Pod 无条件强制删除
            if (getattr(slug_pod.metadata, "labels", None) or {}).get(
                BUILD_DEBUG_LABEL_KEY
            ) == BUILD_DEBUG_LABEL_VALUE:
                logger.info(
                    "Found existing debug Pod<%s/%s>, force delete it for new deployment.",
                    template.namespace,
                    pod_name,
                )
            elif slug_pod.status.phase == PodPhase.RUNNING:
                # 如果 slug 超过了最长执行时间，尝试删除并重新创建，否则取消本次创建
                if not self.check_pod_timeout(slug_pod):
                    raise ResourceDuplicate(
                        "Pod", pod_name, extra_value=self.get_pod_timeout(slug_pod).humanize(locale="zh")
                    )

                logger.info(
                    "%s has running more than %s, delete it and re-create one",
                    pod_name,
                    settings.MAX_SLUG_SECONDS,
                )
            else:
                logger.info(
                    "Found existing finished Pod<%s/%s>, delete it and re-create one.", template.namespace, pod_name
                )

            self._delete_pod(namespace=template.namespace, pod_name=pod_name, grace_period_seconds=0).wait()

        env_list = []
        for key, value in template.runtime.envs.items():
            env_list.append(dict(name=str(key), value=str(value)))

        # 构建调试模式: 注入 Startup Probe + Readiness Probe
        container_spec: Dict = {
            "env": env_list,
            "image": template.runtime.image,
            "name": pod_name,
            "imagePullPolicy": template.runtime.image_pull_policy,
            "resources": template.runtime.resources,
        }

        if template.build_debug:
            # failureThreshold 根据 BUILD_PROCESS_TIMEOUT 动态计算
            probe_timeout = max(settings.BUILD_PROCESS_TIMEOUT, 60)
            failure_threshold = (probe_timeout - 30) // 3
            container_spec.update(
                {
                    "startupProbe": {
                        "exec": {"command": ["test", "-f", "/tmp/build-done"]},
                        "initialDelaySeconds": 30,
                        "periodSeconds": 3,
                        "failureThreshold": failure_threshold,
                    },
                    "readinessProbe": {
                        "exec": {"command": ["test", "-f", "/tmp/build-result-success"]},
                        "initialDelaySeconds": 0,
                        "periodSeconds": 3,
                    },
                }
            )

        # 构建调试模式: 添加 build-debug label
        labels = {"pod_selector": pod_name, "category": "slug-builder"}
        if template.build_debug:
            labels[BUILD_DEBUG_LABEL_KEY] = BUILD_DEBUG_LABEL_VALUE

        slug_pod_body: Dict = {
            "metadata": {
                "name": pod_name,
                "namespace": template.namespace,
                "labels": labels,
            },
            "spec": {
                "containers": [container_spec],
                "restartPolicy": "Never",
                "nodeSelector": template.schedule.node_selector,
                "imagePullSecrets": template.runtime.image_pull_secrets,
            },
            "apiVersion": "v1",
            "kind": "Pod",
        }

        if template.schedule.tolerations:
            slug_pod_body["spec"]["tolerations"] = template.schedule.tolerations

        pod_info, _ = KPod(self.client).create_or_update(
            name=pod_name, namespace=template.namespace, body=slug_pod_body
        )
        return pod_info.metadata.name

    def delete_builder(self, namespace: str, name: str):
        """Force delete a slug builder pod unless it's in "running" phase."""
        pod_name = self.normalize_builder_name(name)
        return self._delete_finished_pod(namespace=namespace, pod_name=pod_name, force=False)

    def interrupt_builder(self, namespace: str, name: str) -> bool:
        """Interrupt build pod by deleting it, this method will wait up to 1 second before a SIGKILL
        signal was sent.

        :param name: the builder name
        :return: True if pod was successfully deleted; False if no pods can be found or any ApiException has
            been raised.
        """
        pod_name = self.normalize_builder_name(name)
        logger.debug(f"interrupting slugbuilder pod:{pod_name}...")
        try:
            self._delete_pod(namespace, pod_name, raise_if_non_exists=True)
        except ResourceMissing:
            logger.warning("Try to interrupt slugbuilder pod, but the pod have gone!")
            return False
        except ApiException:
            logger.exception("Failed to interrupt slugbuilder pod!")
            return False
        else:
            return True

    def wait_for_succeeded(
        self, namespace: str, name: str, timeout: Optional[float] = None, check_period: float = 0.5
    ):
        """Calling this function will blocks until the pod's status has become Succeeded

        :param name: the builder name
        :raises: PodNotSucceededError when Pod does not succeed in given timeout seconds
        """
        pod_name = self.normalize_builder_name(name)
        return self._wait_pod_succeeded(
            namespace=namespace, pod_name=pod_name, timeout=timeout, check_period=check_period
        )

    def wait_for_logs_readiness(self, namespace: str, name: str, timeout: int):
        """Waits for slugbuilder Pod to become ready for retrieving logs

        :param name: the builder name
        :param timeout: max timeout
        """
        pod_name = self.normalize_builder_name(name)
        log_available_statuses = {PodPhase.RUNNING, PodPhase.SUCCEEDED, PodPhase.FAILED}
        KPod(self.client).wait_for_status(
            name=pod_name, namespace=namespace, target_statuses=log_available_statuses, timeout=timeout
        )

    def get_build_log(self, namespace: str, name: str, timeout: int, **kwargs):
        """Get logs of building process

        :param name: the builder name
        """
        pod_name = self.normalize_builder_name(name)
        return super()._get_pod_logs(namespace=namespace, pod_name=pod_name, timeout=timeout, **kwargs)

    @staticmethod
    def normalize_builder_name(name: str) -> str:
        """Get A k8s friendly pod name.

        Although we return as is now, we reserve the ability to normalize/modify this name

        :param name: builder name of engine app
        """
        return name

    def get_pod(self, namespace: str, name: str) -> "Optional[km.V1Pod]":
        """Get the builder Pod object, returns None if not found.

        :param name: the builder name
        """
        pod_name = self.normalize_builder_name(name)
        try:
            return parse_pod(KPod(self.client).get(pod_name, namespace=namespace))
        except ResourceMissing:
            return None

    def check_probe_and_pod(self, namespace: str, name: str) -> BuildProbeStatus:
        """通过容器状态和容器探针来检查构建进程的状态

        检测顺序 (先是检查状态, 再检查探针):
        1. 如果 Pod 处于终止阶段 (成功/失败), 则返回 POD_ENDED
        2. 如果 Pod 正在运行, 检查 containerStatus.started 和 containerStatus.ready 探针

        :param namespace: Pod namespace
        :param name: builder 名称
        :returns: BuildProbeStatus 枚举
        :raises: 如果 Pod 没有找到将 raise ResourceMissing
        """
        pod_name = self.normalize_builder_name(name)
        pod = parse_pod(KPod(self.client).get(pod_name, namespace=namespace))
        phase = pod.status.phase

        # Phase 优先: terminal 状态意味着 Pod 已经结束
        if phase in (PodPhase.SUCCEEDED, PodPhase.FAILED):
            return BuildProbeStatus.POD_ENDED

        # Pod 正在运行, 检查容器探针状态
        container_statuses = pod.status.container_statuses or []
        if not container_statuses:
            return BuildProbeStatus.BUILDING

        c_status = container_statuses[0]
        started = getattr(c_status, "started", False)
        ready = getattr(c_status, "ready", False)

        if not started:
            return BuildProbeStatus.BUILDING
        elif ready:
            return BuildProbeStatus.SUCCEEDED
        else:
            return BuildProbeStatus.FAILED

    def set_build_finished_at(self, namespace: str, name: str):
        """Patch build_finished_at 注解到 builder Pod, 以进行调试窗口的追踪

        :param namespace: Pod namespace
        :param name: builder 名称
        """
        pod_name = self.normalize_builder_name(name)
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        patch_body = {"metadata": {"annotations": {"build_finished_at": now}}}
        try:
            KPod(self.client).patch(pod_name, namespace=namespace, body=patch_body)
        except Exception:
            logger.exception("Failed to patch build_finished_at annotation on Pod<%s/%s>", namespace, pod_name)

    @staticmethod
    def is_debug_window_available(pod, timeout_seconds: int) -> bool:
        """检查调试的构建 Pod 是否还可用 (未过期), 基于 "build_finished_at" 注解.

        注解缺失表示构建尚未完成或刚完成但注解尚未写入, 此时调试窗口尚未开启, 返回 False.
        注解格式异常时同样返回 False, 防止因解析失败而错误放行.

        :param pod: Pod 对象 (必须有 metadata.annotations).
        :param timeout_seconds: 调试窗口持续时间 (单位为 秒)
        :returns: 如果构建窗口可用返回 True
        """
        annotations = pod.metadata.annotations or {}
        finished_at_raw = annotations.get("build_finished_at")
        if not finished_at_raw:
            return False
        try:
            return arrow.now() < arrow.get(finished_at_raw).shift(seconds=timeout_seconds)
        except Exception:  # noqa: BLE001
            logger.warning("Failed to parse build_finished_at annotation, treating as unavailable")
            return False


class CommandHandler(PodScheduleHandler):
    """Handler for running command"""

    def run(self, command: Command) -> str:
        """Run a command, it create the namespace and image credentials automatically.

        :param command: The command object.
        :return: The name of the command.
        """
        NamespacesHandler.new_by_app(command.app).ensure_namespace(command.app.namespace)
        ensure_image_credentials_secret(command.app)
        return self.run_command(command)

    def run_command(self, command: Command) -> str:
        """Run a command."""
        namespace = command.app.namespace
        pod_name = command.name

        try:
            existed = command_kmodel.get(command.app, command.name)
        except AppEntityNotFound:
            logger.info("Command Pod<%s/%s> does not exist, will create one", namespace, pod_name)
            command_kmodel.save(command)
            return command.name

        if existed.phase == PodPhase.RUNNING:
            # 如果 slug 超过了最长执行时间，尝试删除并重新创建，否则取消本次创建
            if not self.check_pod_timeout(existed):
                raise ResourceDuplicate(
                    "Pod", pod_name, extra_value=self.get_pod_timeout(existed).humanize(locale="zh")
                )

            logger.info(
                "%s has running more than %s, delete it and re-create one",
                pod_name,
                settings.MAX_SLUG_SECONDS,
            )

        command_kmodel.delete(existed).wait()
        command_kmodel.save(command)
        return command.name

    def delete_command(self, command: Command):
        namespace = command.app.namespace

        try:
            existed = command_kmodel.get(command.app, command.name)
        except AppEntityNotFound:
            logger.info("Command Pod<%s/%s> does not exist, skip delete", namespace, command.name)
            return None

        if existed.phase == PodPhase.RUNNING and existed.main_container_exit_code is None:
            logger.warning(f"trying to clean Pod<{namespace}/{command.name}>, but it's still running.")
            return None

        return command_kmodel.delete(existed)

    def interrupt_command(self, command: Command) -> bool:
        """Interrupt a command pod by deleting it, this method will wait up to 1 second before a SIGKILL
        signal was sent.

        :param namespace: namespace where run the command.
        :param command: Command to run.
        :return: True if pod was successfully deleted; False if no pods can be found or any ApiException has
            been raised.
        """
        logger.debug(f"interrupting command pod:{command.name}...")
        try:
            existed = command_kmodel.get(command.app, command.name)
            command_kmodel.delete(existed)
        except AppEntityNotFound:
            logger.warning("Try to interrupt command pod, but the pod have gone!")
            return False
        except ApiException:
            logger.exception("Failed to interrupt command pod!")
            return False
        return True

    def wait_for_succeeded(self, command: Command, timeout: Optional[float] = None, check_period: float = 0.5):
        """Calling this function will block until the main container exited

        :raises: PodAbsentError when Pod is not found
        :raises: PodTimeoutError when Pod does not succeed in given timeout seconds
        """
        namespace = command.app.namespace
        pod_name = command.name
        time_started = time.time()
        while timeout is None or time.time() - time_started < timeout:
            try:
                command_in_k8s = command_kmodel.get(command.app, command.name)
            except AppEntityNotFound as e:
                raise PodAbsentError(f"Pod<{namespace}/{pod_name}> not found") from e

            # Pod 执行成功或主容器正常退出, 视为成功
            if command_in_k8s.phase == PodPhase.SUCCEEDED or command_in_k8s.main_container_exit_code == os.EX_OK:
                return True
            elif command_in_k8s.phase == PodPhase.RUNNING:
                time.sleep(check_period)
                continue

            # 执行可能出现异常, 需要从 pod 中查询更多详情
            v1pod = parse_pod(command_in_k8s._kube_data)
            health_status = check_pod_health_status(v1pod)
            if health_status.status == HealthStatusType.PROGRESSING:
                # PROGRESSING 意味着 Pod 处于 Pending 且无异常事件(例如拉取镜像异常; 无节点可调度等), 继续等待
                time.sleep(check_period)
                continue

            exit_code = extract_exit_code(health_status) or command_in_k8s.main_container_exit_code
            raise PodNotSucceededError(
                f"Pod<{namespace}/{pod_name}> ends unsuccessfully",
                reason=health_status.reason,
                message=health_status.message,
                exit_code=exit_code,
            )
        raise PodTimeoutError(f"Pod<{namespace}/{pod_name}> didn't succeeded in {timeout} seconds.")

    def wait_for_logs_readiness(self, command: Command, timeout: int):
        """Waits for command Pod to become ready for retrieving logs

        :param namespace: namespace where run the command.
        :param command: Command to run.
        :param timeout: max timeout
        """
        log_available_statuses = {PodPhase.RUNNING, PodPhase.SUCCEEDED, PodPhase.FAILED}
        KPod(self.client).wait_for_status(
            namespace=command.app.namespace,
            name=command.name,
            target_statuses=log_available_statuses,
            timeout=timeout,
        )

    def get_command_logs(self, command: Command, timeout: int, **kwargs):
        """Get logs of the command.

        :param namespace: namespace where run the command.
        :param command: Command to run.
        """
        return self._get_pod_logs(
            namespace=command.app.namespace, pod_name=command.name, timeout=timeout, container=command.name, **kwargs
        )

    def check_pod_timeout(self, pod: Command) -> bool:
        """Check A Pod whether running too long"""
        now = arrow.get(localtime())
        when_timeout = self.get_pod_timeout(pod)
        return when_timeout <= now

    @staticmethod
    def get_pod_timeout(pod: Command) -> arrow.Arrow:
        # 注意：如果 Pod StartTime 为空，则不会超时（保留现场）
        start_time = arrow.get(pod.start_time) if pod.start_time else arrow.now()
        return start_time + datetime.timedelta(seconds=settings.MAX_SLUG_SECONDS)


class ProcAutoscalingHandler(ResourceHandlerBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manager: AppEntityManager[ProcAutoscaling, "WlApp"] = AppEntityManager(ProcAutoscaling)

    def deploy(self, scaling: ProcAutoscaling):
        """向集群中下发 GPA （创建/更新）"""
        try:
            existed = self.manager.get(app=scaling.app, name=scaling.name)
            scaling._kube_data = existed._kube_data
        except AppEntityNotFound:
            self.manager.create(scaling)
        else:
            self.manager.update(scaling, "patch", allow_not_concrete=True, content_type="application/merge-patch+json")

    def delete(self, scaling: ProcAutoscaling):
        """删除集群中的 GPA"""
        self.manager.delete_by_name(scaling.app, scaling.name)


class BkAppHookHandler:
    def __init__(self, app: "WlApp", hook_name: str):
        """
        :param app: app hook belongs to
        :param hook_name: hook pod name
        """
        self.client = get_client_by_app(app)
        self.namespace = app.namespace
        self.hook_name = hook_name

    def wait_for_logs_readiness(self, timeout: float = 20):
        """Waits for hook pod to become ready for retrieving logs

        :param timeout: max timeout
        """
        log_available_statuses = {PodPhase.RUNNING, PodPhase.SUCCEEDED, PodPhase.FAILED}
        KPod(self.client).wait_for_status(
            namespace=self.namespace,
            name=self.hook_name,
            target_statuses=log_available_statuses,
            timeout=timeout,
        )

    def fetch_logs(self, follow: bool = False):
        """Fetch logs of running hook pod"""
        return KPod(self.client).get_log(name=self.hook_name, namespace=self.namespace, follow=follow)

    def wait_hook_finished(self, timeout: float = 60 * 5) -> PodPhase:
        """Waits for hook pod to finish"""
        finished_statuses = {PodPhase.SUCCEEDED, PodPhase.FAILED}
        status = KPod(self.client).wait_for_status(
            namespace=self.namespace,
            name=self.hook_name,
            target_statuses=finished_statuses,
            timeout=timeout,
        )
        return PodPhase(status)
