# -*- coding: utf-8 -*-
import datetime
import logging
from typing import Dict, List

from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from paas_wl.cnative.specs.models import AppModelDeploy
from paas_wl.platform.applications.constants import ApplicationType
from paas_wl.platform.applications.models import EngineApp, Release
from paas_wl.platform.applications.struct_models import ModuleEnv
from paas_wl.resources.actions.scale import AppScale
from paas_wl.resources.actions.stop import AppStop
from paas_wl.resources.kube_res.exceptions import AppEntityNotFound
from paas_wl.workloads.processes.constants import ProcessTargetStatus
from paas_wl.workloads.processes.exceptions import ProcessOperationTooOften
from paas_wl.workloads.processes.models import Process, ProcessSpec
from paas_wl.workloads.processes.readers import instance_kmodel, process_kmodel

logger = logging.getLogger(__name__)


class AppProcessesController:
    """Controls an EngineApp's processes, includes common operations such as
    "start", "stop" and "scale", this class will update both the "ProcessSpec"(persistent
    structure in database) and the related resources in Cluster.
    """

    def __init__(self, app: EngineApp):
        """
        :param app:
        :param skip_judge_frequent: whether raise exception when action happens too frequently, default to True
        """
        self.app = app

    def start(self, proc_spec: ProcessSpec):
        """Start a process, WILL update the service if necessary

        :param proc_spec: process spec object
        """
        if proc_spec.target_replicas <= 0:
            proc_spec.target_replicas = 1
        proc_spec.target_status = ProcessTargetStatus.START.value
        proc_spec.save(update_fields=['target_replicas', 'target_status', 'updated'])

        AppScale(app=self.app).perform(proc_spec.name)

    def stop(self, proc_spec: ProcessSpec):
        """Stop a process by setting replicas to zero, WILL NOT delete the service.

        :param proc_spec: process spec object
        """
        proc_spec.target_status = ProcessTargetStatus.STOP.value
        proc_spec.save(update_fields=['target_status', 'updated'])

        AppStop(app=self.app).perform(proc_spec.name)

    def scale(self, proc_spec: ProcessSpec, target_replicas: int):
        """Scale a process to target replicas, WILL update the service if necessary

        :param proc_spec: process spec object
        :param target_replicas: the expected replicas, '0' for stop
        :raises: ValueError when target_replicas is too big
        """
        proc_spec.target_replicas = target_replicas
        proc_spec.target_status = (
            ProcessTargetStatus.START.value if target_replicas else ProcessTargetStatus.STOP.value
        )
        proc_spec.save(update_fields=['target_replicas', 'target_status', 'updated'])

        AppScale(app=self.app).perform(proc_spec.name)

    def get_processes_status(self) -> List[Process]:
        """Get the real-time processes status

        1. Get current process structure from `release.structure`
        2. Get process status from `process_kmodel` & `instance_kmodel`
        """
        results: List[Process] = []

        try:
            procfile = Release.objects.get_latest(self.app).get_procfile()
        except Exception as e:
            logger.info("Release does not exists. Detail: %s", e)
            return results

        for process_type in procfile:
            try:
                process = process_kmodel.get_by_type(self.app, process_type)
                process.instances = instance_kmodel.list_by_process_type(self.app, process_type)
            except AppEntityNotFound:
                logger.info("process<%s/%s> missing in k8s cluster" % (self.app.name, process_type))
                continue

            results.append(process)
        return results


def list_proc_specs(engine_app: EngineApp) -> List[Dict]:
    """Return all processes's specs of an app

    :return: list of process specs
    """
    from .drf_serializers import ProcessSpecSLZ

    results = []
    for process_type in engine_app.process_specs.all().values_list("name", flat=True):
        proc_spec = ProcessSpec.objects.get(engine_app=engine_app, name=process_type)
        results.append(ProcessSpecSLZ(proc_spec).data)
    return results


def judge_operation_frequent(process_spec: ProcessSpec, operation_interval: datetime.timedelta):
    """检查 process 操作是否频繁"""
    if (timezone.now() - process_spec.updated) < operation_interval:
        raise ProcessOperationTooOften(_(f"进程操作过于频繁，请间隔 {operation_interval.total_seconds()} 秒再试。"))


def env_is_running(env: ModuleEnv) -> bool:
    """Check if an env is running, which mean a successful deployment is available
    for the env. This status is useful in many situations, such as creating a custom
    domain and etc.

    :param env: The environment object
    :return: Whether current env is running
    """
    if env.application.type == ApplicationType.CLOUD_NATIVE:
        return AppModelDeploy.objects.any_successful(env)
    else:
        engine_app = EngineApp.objects.get_by_env(env)
        return Release.objects.any_successful(engine_app)
