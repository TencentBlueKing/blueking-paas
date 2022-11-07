# -*- coding: utf-8 -*-
import datetime
import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Optional, Tuple

import arrow
from django.conf import settings
from django.utils.timezone import localtime
from kubernetes import client as client_mod
from kubernetes.client.rest import ApiException

from paas_wl.release_controller.hooks.entities import Command, command_kmodel
from paas_wl.resources.base.constants import BKAPP_CATEGORY
from paas_wl.resources.base.exceptions import (
    CreateServiceAccountTimeout,
    PodNotSucceededAbsentError,
    PodNotSucceededError,
    PodNotSucceededTimeoutError,
    ResourceDeleteTimeout,
    ResourceDuplicate,
    ResourceMissing,
)
from paas_wl.resources.base.kres import KNamespace, KPod
from paas_wl.resources.kube_res.base import AppEntityManager
from paas_wl.resources.kube_res.exceptions import AppEntityNotFound
from paas_wl.utils.kubestatus import (
    HealthStatus,
    HealthStatusType,
    check_pod_health_status,
    extract_exit_code,
    parse_pod,
)
from paas_wl.workloads.processes.models import Process

if TYPE_CHECKING:
    from paas_wl.release_controller.builder.infras import SlugBuilderTemplate
    from paas_wl.resources.base.base import EnhancedApiClient
    from paas_wl.resources.base.generation import MapperPack

logger = logging.getLogger(__name__)


@dataclass
class ResourceHandlerBase:
    client: 'EnhancedApiClient'
    default_connect_timeout: int
    default_request_timeout: tuple
    mapper_version: 'MapperPack'


class ProcessesHandler(ResourceHandlerBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.process_manager = AppEntityManager(Process)

    def deploy(self, process: Process):
        try:
            self.process_manager.update(
                process, "replace", mapper_version=self.mapper_version, allow_not_concrete=True
            )
        except AppEntityNotFound:
            self.process_manager.create(process, mapper_version=self.mapper_version)

    def delete(self, process: Process):
        self.mapper_version.deployment(process=process).delete(non_grace_period=True)

        # we have to delete rs & pod manually
        self.mapper_version.replica_set(process=process).delete_collection()
        self.mapper_version.pod(process=process).delete_individual()

    def scale(self, process: Process):
        """focus on deployment replicas"""
        try:
            self.process_manager.update(process, "patch", mapper_version=self.mapper_version)
        except AppEntityNotFound:
            self.process_manager.create(process, mapper_version=self.mapper_version)

    @staticmethod
    def get_process_type(deployment):
        name = deployment.metadata.name
        namespace = deployment.metadata.namespace
        labels = deployment.metadata.labels

        # get process type
        process_type = labels.get("process_id")
        # we have to handle old deployments which is without labels,
        # example: namespace: bkapp-test2-stag, name: ieod-bkapp-test2-stag-web-gunicorn-deployment
        if not process_type:
            process_type = name.split(namespace)[-1].split("-")[1]

        return process_type

    #########
    # batch #
    #########

    def get_abnormal_deployments(self, region):
        """查询整个命名空间下的deployments，并通过replica，获取异常状态的deployments"""
        # TODO: remove when phalanx is ready for doing this
        all_deployments = client_mod.ExtensionsV1beta1Api(self.client).list_deployment_for_all_namespaces(
            _request_timeout=self.default_request_timeout
        )

        # format: {"engine_app_name": ["process_type"]}
        abnormal_deployments = []
        for deployment in all_deployments.items:
            labels = deployment.spec.template.metadata.labels
            # TODO: 为兼容已经部署的应用，现阶段先跳过校验labels中的region/category为空的应用
            curr_region = labels.get("region")
            curr_category = labels.get("category")
            if curr_region not in [None, region]:
                continue
            if not (curr_category in [None, BKAPP_CATEGORY] and deployment.metadata.namespace.startswith('bkapp')):
                continue

            if deployment.status.available_replicas:
                exist_failed_replica = int(deployment.spec.replicas) != int(deployment.status.available_replicas)
            else:
                exist_failed_replica = bool(int(deployment.spec.replicas))

            if exist_failed_replica:
                abnormal_deployments.append(deployment)

        return abnormal_deployments

    #################
    # inner methods #
    #################


class NamespacesHandler(ResourceHandlerBase):
    """Handler for namespace resources"""

    def delete(self, namespace):
        KNamespace(self.client).delete(namespace)

    def create(self, namespace):
        """
        :return: instance of namespace, created
        """
        return KNamespace(self.client).get_or_create(namespace)

    def check_service_account_secret(self, namespace, max_wait_seconds=15):
        try:
            KNamespace(self.client).wait_for_default_sa(namespace, timeout=max_wait_seconds)
        except CreateServiceAccountTimeout:
            logger.error("timeout while wating for the default sa of %s to be created", namespace)
            raise


class WaitPodDelete:
    _check_interval = 1

    def __init__(self, namespace: str, name: str, client: 'EnhancedApiClient'):
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
                pod = KPod(self.client).get(name=self.name, namespace=self.namespace)
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
            if pod.status.phase == "Running" and not force:
                logger.warning(f"trying to clean Pod<{namespace}/{pod_name}>, but it's still running.")
                return

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
            non_grace_period=True if grace_period_seconds == 0 else False,
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
        :raises: PodNotSucceededError when Pod does not succeed in given timeout seconds
        """
        time_started = time.time()
        while timeout is None or time.time() - time_started < timeout:
            try:
                pod_phase, health_status = self._get_pod_status(namespace, pod_name)
            except ResourceMissing as e:
                raise PodNotSucceededAbsentError(f"Pod<{namespace}/{pod_name}> not found") from e

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
        raise PodNotSucceededTimeoutError(f"Pod<{namespace}/{pod_name}> didn't succeeded in {timeout} seconds.")

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

    def build_slug(self, template: 'SlugBuilderTemplate'):
        """Start a Pod for building slug

        :param template: the template to run builder
        """
        pod_name = self.normalize_builder_name(template.name)
        try:
            slug_pod = KPod(self.client).get(pod_name, namespace=template.namespace)
        except ResourceMissing:
            logger.info("build slug<%s/%s> does not exist, will create one", template.namespace, template.name)
        else:
            # ignore the other pods
            if slug_pod.status.phase == "Running":
                # 如果 slug 超过了最长执行时间，尝试删除并重新创建，否则取消本次创建
                if not self.check_pod_timeout(slug_pod):
                    raise ResourceDuplicate(
                        'Pod', pod_name, extra_value=self.get_pod_timeout(slug_pod).humanize(locale="zh")
                    )

                logger.info(
                    "%s has running more than %s, delete it and re-create one",
                    pod_name,
                    settings.MAX_SLUG_SECONDS,
                )

            self._delete_pod(namespace=template.namespace, pod_name=pod_name, grace_period_seconds=0).wait()

        env_list = []
        for key, value in template.runtime.envs.items():
            env_list.append(dict(name=str(key), value=str(value)))

        slug_pod_body: Dict = {
            'metadata': {
                'name': pod_name,
                'namespace': template.namespace,
                'labels': {'pod_selector': pod_name, 'category': 'slug-builder'},
            },
            'spec': {
                'containers': [
                    {
                        'env': env_list,
                        'image': template.runtime.image,
                        'name': pod_name,
                        'imagePullPolicy': template.runtime.image_pull_policy,
                        'resources': settings.SLUGBUILDER_RESOURCES_SPEC,
                    },
                ],
                'restartPolicy': 'Never',
                'nodeSelector': template.schedule.node_selector,
                'imagePullSecrets': template.runtime.image_pull_secrets,
            },
            'apiVersion': 'v1',
            'kind': 'Pod',
        }

        if template.schedule.tolerations:
            slug_pod_body['spec']['tolerations'] = template.schedule.tolerations

        pod_info, _ = KPod(self.client).create_or_update(
            name=pod_name, namespace=template.namespace, body=slug_pod_body
        )
        return pod_info.metadata.name

    def delete_slug(self, namespace: str, name: str):
        """Force delete slugbuilder pod unless it's in "running" phase"""
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
        log_available_statuses = {"Running", "Succeeded", "Failed"}
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


class CommandHandler(PodScheduleHandler):
    """Handler for running command"""

    def run_command(
        self,
        command: Command,
    ):
        namespace = command.app.namespace
        pod_name = command.name

        try:
            existed: Command = command_kmodel.get(command.app, command.name)
        except AppEntityNotFound:
            logger.info("Command Pod<%s/%s> does not exist, will create one" % (namespace, pod_name))
            command_kmodel.save(command)
            return command.name

        if existed.status == "Running":
            # 如果 slug 超过了最长执行时间，尝试删除并重新创建，否则取消本次创建
            if not self.check_pod_timeout(existed):
                raise ResourceDuplicate(
                    'Pod', pod_name, extra_value=self.get_pod_timeout(existed).humanize(locale="zh")
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
            logger.info("Command Pod<%s/%s> does not exist, skip delete" % (namespace, command.name))
            return

        if existed.status == "Running":
            logger.warning(f"trying to clean Pod<{namespace}/{command.name}>, but it's still running.")
            return

        return command_kmodel.delete(existed)

    def interrupt_command(self, command: Command) -> bool:
        """Interrupt build pod by deleting it, this method will wait up to 1 second before a SIGKILL
        signal was sent.

        :param namespace: namespace where run the command.
        :param command: Command to run.
        :return: True if pod was successfully deleted; False if no pods can be found or any ApiException has
            been raised.
        """
        logger.debug(f"interrupting command pod:{command.name}...")
        try:
            existed: Command = command_kmodel.get(command.app, command.name)
            command_kmodel.delete(existed)
        except AppEntityNotFound:
            logger.warning("Try to interrupt command pod, but the pod have gone!")
            return False
        except ApiException:
            logger.exception("Failed to interrupt command pod!")
            return False
        return True

    def wait_for_succeeded(self, command: Command, timeout: Optional[float] = None, check_period: float = 0.5):
        return self._wait_pod_succeeded(
            namespace=command.app.namespace,
            pod_name=command.name,
            timeout=timeout,
            check_period=check_period,
        )

    def wait_for_logs_readiness(self, command: Command, timeout: int):
        """Waits for command Pod to become ready for retrieving logs

        :param namespace: namespace where run the command.
        :param command: Command to run.
        :param timeout: max timeout
        """
        log_available_statuses = {"Running", "Succeeded", "Failed"}
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
        return self._get_pod_logs(namespace=command.app.namespace, pod_name=command.name, timeout=timeout, **kwargs)

    def check_pod_timeout(self, pod: Command) -> bool:
        """Check A Pod whether running too long"""
        now = arrow.get(localtime())
        when_timeout = self.get_pod_timeout(pod)
        return when_timeout <= now

    @staticmethod
    def get_pod_timeout(pod: Command) -> arrow.Arrow:
        return arrow.get(pod.start_time) + datetime.timedelta(seconds=settings.MAX_SLUG_SECONDS)
