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
# TODO: Add Tests for both controller classes
import logging
from dataclasses import asdict
from typing import Optional

from paas_wl.bk_app.cnative.specs.procs.exceptions import ProcNotFoundInRes
from paas_wl.bk_app.cnative.specs.procs.replicas import ProcReplicas
from paas_wl.bk_app.deploy.app_res.utils import get_scheduler_client_by_app
from paas_wl.bk_app.processes.constants import DEFAULT_CNATIVE_MAX_REPLICAS, ProcessTargetStatus
from paas_wl.bk_app.processes.controllers import ProcControllerHub
from paas_wl.bk_app.processes.exceptions import ProcessNotFound, ScaleProcessError
from paas_wl.bk_app.processes.models import ProcessSpec
from paas_wl.infras.cluster.constants import ClusterFeatureFlag
from paas_wl.infras.cluster.utils import get_cluster_by_app
from paas_wl.infras.resources.base.base import get_client_by_cluster_name
from paas_wl.infras.resources.base.kres import KDeployment
from paas_wl.infras.resources.generation.version import get_proc_deployment_name
from paas_wl.workloads.autoscaling.entities import AutoscalingConfig, ScalingObjectRef
from paas_wl.workloads.autoscaling.exceptions import AutoscalingUnsupported
from paas_wl.workloads.autoscaling.kres_entities import ProcAutoscaling
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.bkapp_model.manager import ModuleProcessSpecManager

logger = logging.getLogger(__name__)


class AppProcessesController:
    """Controls app's processes, includes common operations such as
    "start", "stop" and "scale", this class will update both the "ProcessSpec"(persistent
    structure in database) and the related resources in Cluster.

    Only support default applications.
    """

    def __init__(self, env: ModuleEnvironment):
        self.app = env.wl_app
        self.env = env
        self.client = get_scheduler_client_by_app(self.app)

    def start(self, proc_type: str):
        """Start a process, WILL update the service if necessary

        :param proc_type: process type
        :raise: ScaleProcessError when error occurs
        """
        spec_updater = ProcSpecUpdater(self.env, proc_type)
        spec_updater.set_start()
        proc_spec = spec_updater.spec_object
        try:
            self.client.scale_process(self.app, proc_spec.name, proc_spec.target_replicas)
        except Exception as e:
            raise ScaleProcessError(f"scale {proc_spec.name} failed, reason: {e}")

    def stop(self, proc_type: str):
        """Stop a process by setting replicas to zero, WILL NOT delete the service.

        :param proc_type: process type
        :raise: ScaleProcessError when error occurs
        """
        spec_updater = ProcSpecUpdater(self.env, proc_type)
        spec_updater.set_stop()
        proc_spec = spec_updater.spec_object
        try:
            self.client.shutdown_process(self.app, proc_spec.name)
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

        spec_updater = ProcSpecUpdater(self.env, proc_type)
        spec_updater.change_replicas(target_replicas)
        proc_spec = spec_updater.spec_object
        try:
            self.client.scale_process(self.app, proc_spec.name, proc_spec.target_replicas)
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
            name=get_proc_deployment_name(self.app, proc_type),
        )

        return ProcAutoscaling(self.app, proc_type, scaling_config, target_ref)  # type: ignore


class CNativeProcController:
    """Process controller for cloud-native applications"""

    def __init__(self, env: ModuleEnvironment):
        self.env = env

    def start(self, proc_type: str):
        """Start a process."""
        spec_updater = ProcSpecUpdater(self.env, proc_type)
        spec_updater.set_start()
        try:
            ProcReplicas(self.env).scale(proc_type, spec_updater.spec_object.target_replicas)
        except ProcNotFoundInRes as e:
            raise ProcessNotFound(str(e))

    def stop(self, proc_type: str):
        """Stop a process."""
        spec_updater = ProcSpecUpdater(self.env, proc_type)
        spec_updater.set_stop()
        try:
            ProcReplicas(self.env).scale(proc_type, 0)
        except ProcNotFoundInRes as e:
            raise ProcessNotFound(str(e))

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

        if target_replicas > DEFAULT_CNATIVE_MAX_REPLICAS:
            raise ValueError(f"target_replicas can't be greater than {DEFAULT_CNATIVE_MAX_REPLICAS}")

        ProcSpecUpdater(self.env, proc_type).change_replicas(target_replicas)
        # Update the module specs also to keep the bkapp model in sync.
        ModuleProcessSpecManager(self.env.module).set_replicas(proc_type, self.env.environment, target_replicas)

        try:
            ProcReplicas(self.env).scale(proc_type, target_replicas)
        except ProcNotFoundInRes as e:
            raise ProcessNotFound(str(e))


class ProcSpecUpdater:
    """It update the ProcessSpec object for the given env and process type.

    :param env: The environment object.
    :param proc_type: The process type.
    """

    def __init__(self, env: ModuleEnvironment, proc_type: str):
        self.app = env.wl_app
        self.proc_type = proc_type

    def set_start(self):
        """Set the process to "start" state."""
        proc_spec = self.spec_object
        if proc_spec.target_replicas <= 0:
            proc_spec.target_replicas = 1
        proc_spec.target_status = ProcessTargetStatus.START.value
        proc_spec.save(update_fields=['target_replicas', 'target_status', 'updated'])

    def set_stop(self):
        """Set the process to "stop" state."""
        proc_spec = self.spec_object
        proc_spec.target_status = ProcessTargetStatus.STOP.value
        proc_spec.save(update_fields=['target_status', 'updated'])

    def change_replicas(self, target_replicas: int):
        """Change the target_replicas value."""
        proc_spec = self.spec_object
        proc_spec.target_replicas = target_replicas
        proc_spec.target_status = (
            ProcessTargetStatus.START.value if target_replicas else ProcessTargetStatus.STOP.value
        )
        proc_spec.save(update_fields=['target_replicas', 'target_status', 'updated'])

    @property
    def spec_object(self) -> ProcessSpec:
        """Get the ProcessSpec object"""
        try:
            return ProcessSpec.objects.get(engine_app_id=self.app.uuid, name=self.proc_type)
        except ProcessSpec.DoesNotExist:
            raise ProcessNotFound(self.proc_type)


# Register controllers
ProcControllerHub.register_controller(ApplicationType.DEFAULT, AppProcessesController)
ProcControllerHub.register_controller(ApplicationType.BK_PLUGIN, AppProcessesController)
ProcControllerHub.register_controller(ApplicationType.ENGINELESS_APP, AppProcessesController)

ProcControllerHub.register_controller(ApplicationType.CLOUD_NATIVE, CNativeProcController)
