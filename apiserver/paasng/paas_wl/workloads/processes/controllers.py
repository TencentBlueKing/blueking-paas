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
import datetime
import logging
from dataclasses import asdict
from typing import List, Optional, Protocol

from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from paas_wl.cluster.constants import ClusterFeatureFlag
from paas_wl.cluster.utils import get_cluster_by_app
from paas_wl.cnative.specs.models import AppModelDeploy
from paas_wl.cnative.specs.procs.exceptions import ProcNotFoundInRes
from paas_wl.cnative.specs.procs.replicas import ProcReplicas
from paas_wl.platform.applications.models import Release, WlApp
from paas_wl.resources.base.base import get_client_by_cluster_name
from paas_wl.resources.base.kres import KDeployment
from paas_wl.resources.kube_res.exceptions import AppEntityNotFound
from paas_wl.resources.utils.app import get_scheduler_client_by_app
from paas_wl.workloads.autoscaling.entities import ProcAutoscaling
from paas_wl.workloads.autoscaling.exceptions import AutoscalingUnsupported
from paas_wl.workloads.autoscaling.models import AutoscalingConfig, ScalingObjectRef
from paas_wl.workloads.processes.constants import ProcessTargetStatus
from paas_wl.workloads.processes.entities import Process
from paas_wl.workloads.processes.exceptions import ProcessNotFound, ProcessOperationTooOften, ScaleProcessError
from paas_wl.workloads.processes.managers import AppProcessManager
from paas_wl.workloads.processes.models import ProcessSpec
from paas_wl.workloads.processes.readers import instance_kmodel, process_kmodel
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import ModuleEnvironment

logger = logging.getLogger(__name__)


class ProcController(Protocol):
    """Control app's processes"""

    def start(self, proc_type: str):
        ...

    def stop(self, proc_type: str):
        ...

    def scale(
        self,
        proc_type: str,
        autoscaling: bool = False,
        target_replicas: Optional[int] = None,
        scaling_config: Optional[AutoscalingConfig] = None,
    ):
        ...


class AppProcessesController:
    """Controls app's processes, includes common operations such as
    "start", "stop" and "scale", this class will update both the "ProcessSpec"(persistent
    structure in database) and the related resources in Cluster.

    Only support default applications.
    """

    def __init__(self, env: ModuleEnvironment):
        self.app = env.wl_app
        self.client = get_scheduler_client_by_app(self.app)

    def start(self, proc_type: str):
        """Start a process, WILL update the service if necessary

        :param proc_type: process type
        :raise: ScaleProcessError when error occurs
        """
        proc_spec = self._get_spec(proc_type)
        if proc_spec.target_replicas <= 0:
            proc_spec.target_replicas = 1
        proc_spec.target_status = ProcessTargetStatus.START.value
        proc_spec.save(update_fields=['target_replicas', 'target_status', 'updated'])

        try:
            self.client.scale_processes([self._prepare_process(proc_spec.name)])
        except Exception as e:
            raise ScaleProcessError(f"scale {proc_spec.name} failed, reason: {e}")

    def stop(self, proc_type: str):
        """Stop a process by setting replicas to zero, WILL NOT delete the service.

        :param proc_type: process type
        :raise: ScaleProcessError when error occurs
        """
        proc_spec = self._get_spec(proc_type)
        proc_spec.target_status = ProcessTargetStatus.STOP.value
        proc_spec.save(update_fields=['target_status', 'updated'])

        try:
            self.client.shutdown_processes([self._prepare_process(proc_spec.name)])
        except Exception as e:
            raise ScaleProcessError(f"scale {proc_spec.name} failed, reason: {e}")

    def scale(
        self,
        proc_type: str,
        autoscaling: bool = False,
        target_replicas: Optional[int] = None,
        scaling_config: Optional[AutoscalingConfig] = None,
    ):
        """Scale process to the `target_replicas` or set an autoscaling policy."""
        cluster = get_cluster_by_app(self.app)
        if not cluster.has_feature_flag(ClusterFeatureFlag.ENABLE_AUTOSCALING):
            if not autoscaling:
                return self._scale(proc_type, target_replicas)

            raise AutoscalingUnsupported("autoscaling can't be used because cluster unsupported.")

        scaling = self._build_proc_autoscaling(cluster.name, proc_type, autoscaling, scaling_config)
        if autoscaling:
            return self._deploy_autoscaling(scaling)

        self._disable_autoscaling(scaling)
        return self._scale(proc_type, target_replicas)

    def _scale(self, proc_type: str, target_replicas: Optional[int]):
        """Scale a process to target replicas, WILL update the service if necessary

        :param proc_type: process type
        :param target_replicas: the expected replicas, '0' for stop
        :raises: ValueError when target_replicas is too big
        """
        if target_replicas is None:
            raise ValueError('target_replicas required when scale process')

        proc_spec = self._get_spec(proc_type)
        proc_spec.target_replicas = target_replicas
        proc_spec.target_status = (
            ProcessTargetStatus.START.value if target_replicas else ProcessTargetStatus.STOP.value
        )
        proc_spec.save(update_fields=['target_replicas', 'target_status', 'updated'])

        try:
            self.client.scale_processes([self._prepare_process(proc_spec.name)])
        except Exception as e:
            raise ScaleProcessError(f"scale {proc_spec.name} failed, reason: {e}")

    def _deploy_autoscaling(self, scaling: ProcAutoscaling):
        """Set autoscaling policy for process"""
        proc_spec = self._get_spec(scaling.name)
        # 普通应用：最大副本数 <= 进程规格方案允许的最大副本数
        if scaling.spec.max_replicas > proc_spec.plan.max_replicas:
            raise ScaleProcessError(f"max_replicas in scaling config can't more than {proc_spec.plan.max_replicas}")

        proc_spec.autoscaling = True
        proc_spec.scaling_config = asdict(scaling.spec)
        proc_spec.save(update_fields=['autoscaling', 'scaling_config', 'updated'])

        self.client.deploy_autoscaling(scaling)

    def _disable_autoscaling(self, scaling: ProcAutoscaling):
        """Remove process's autoscaling policy"""
        proc_spec = self._get_spec(scaling.name)

        proc_spec.autoscaling = False
        proc_spec.scaling_config = {}
        proc_spec.save(update_fields=['autoscaling', 'scaling_config', 'updated'])

        self.client.disable_autoscaling(scaling)

    def _prepare_process(self, name: str) -> Process:
        """Create Process object by name, reads properties from different sources:

        1. replicas: defined in Model `ProcessSpec`
        2. command: defined in `WlApp.structure`
        """
        return AppProcessManager(app=self.app).assemble_process(name)

    def _get_spec(self, proc_type: str) -> ProcessSpec:
        try:
            return ProcessSpec.objects.get(engine_app_id=self.app.uuid, name=proc_type)
        except ProcessSpec.DoesNotExist:
            raise ProcessNotFound(proc_type)

    def _build_proc_autoscaling(
        self, cluster_name: str, proc_type: str, autoscaling: bool, scaling_config: Optional[AutoscalingConfig]
    ) -> ProcAutoscaling:
        if autoscaling and not scaling_config:
            raise ValueError('scaling_config required when set autoscaling policy')

        kres_client = KDeployment(get_client_by_cluster_name(cluster_name), api_version='')
        target_ref = ScalingObjectRef(
            api_version=kres_client.get_preferred_version(),
            kind=kres_client.kind,
            name=self._prepare_process(proc_type).name,
        )

        return ProcAutoscaling(self.app, proc_type, scaling_config, target_ref)  # type: ignore


def judge_operation_frequent(app: WlApp, proc_type: str, operation_interval: datetime.timedelta):
    """检查 process 操作是否频繁

    - Only normal app which owns ProcessSpec objects is supported
    - Last operated time was stored in ProcessSpec.updated
    """
    try:
        spec = ProcessSpec.objects.get(engine_app_id=app.uuid, name=proc_type)
    except ProcessSpec.DoesNotExist:
        return

    if (timezone.now() - spec.updated) < operation_interval:
        raise ProcessOperationTooOften(_(f"进程操作过于频繁，请间隔 {operation_interval.total_seconds()} 秒再试。"))


class CNativeProcController:
    """Process controller for cloud-native applications"""

    # A hard limit on count
    # TODO: Replace it with more concise solutions
    HARD_LIMIT_COUNT = 10

    def __init__(self, env: ModuleEnvironment):
        self.env = env

    def start(self, proc_type: str):
        """Start a process"""
        # TODO: Read target replicas from existed resource to maintain consistency
        default_replicas = 1
        return self.scale(proc_type, target_replicas=default_replicas)

    def stop(self, proc_type: str):
        """Stop a process by setting replicas to zero"""
        return self.scale(proc_type, target_replicas=0)

    def scale(
        self,
        proc_type: str,
        autoscaling: bool = False,
        target_replicas: Optional[int] = None,
        scaling_config: Optional[AutoscalingConfig] = None,
    ):
        """Scale process to the `target_replicas` or set an autoscaling policy."""
        if autoscaling:
            raise NotImplementedError('work in progress')

        # can't use `if not target_replicas` because stop process will use `scale(proc_type, target_replicas=0)`
        if target_replicas is None:
            raise ValueError('target_replicas required when scale process')

        if target_replicas > self.HARD_LIMIT_COUNT:
            raise ValueError(f"target_replicas can't be greater than {self.HARD_LIMIT_COUNT}")

        try:
            ProcReplicas(self.env).scale(proc_type, target_replicas)
        except ProcNotFoundInRes as e:
            raise ProcessNotFound(str(e))


def get_proc_ctl(env: ModuleEnvironment) -> ProcController:
    """Get a process controller by env"""
    if env.application.type == ApplicationType.CLOUD_NATIVE:
        return CNativeProcController(env)
    return AppProcessesController(env)


def get_processes_status(app: WlApp) -> List[Process]:
    """Get the real-time processes status

    1. Get current process structure from `release.structure`
    2. Get process status from `process_kmodel` & `instance_kmodel`
    """
    results: List[Process] = []

    # TODO: fixme 云原生应用没有 Release!!!
    try:
        release: Release = Release.objects.get_latest(app)
        procfile = release.get_procfile()
    except Release.DoesNotExist:
        return results

    for process_type in procfile:
        try:
            process = process_kmodel.get_by_type(app, process_type)
            process.instances = instance_kmodel.list_by_process_type(app, process_type)
        except AppEntityNotFound:
            logger.info("process<%s/%s> missing in k8s cluster" % (app.name, process_type))
            continue

        results.append(process)
    return results


def env_is_running(env: ModuleEnvironment) -> bool:
    """Check if an env is running, which mean a successful deployment is available
    for the env. This status is useful in many situations, such as creating a custom
    domain and etc.

    :param env: The environment object
    :return: Whether current env is running
    """
    if env.application.type == ApplicationType.CLOUD_NATIVE:
        return AppModelDeploy.objects.any_successful(env) and not env.is_offlined
    else:
        wl_app = env.wl_app
        return Release.objects.any_successful(wl_app) and not env.is_offlined
