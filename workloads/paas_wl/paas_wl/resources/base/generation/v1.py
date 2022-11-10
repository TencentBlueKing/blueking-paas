# -*- coding: utf-8 -*-
from paas_wl.platform.applications.models import App
from paas_wl.platform.applications.models.managers.app_metadata import get_metadata
from paas_wl.resources.base.kres import KDeployment, KPod, KReplicaSet
from paas_wl.workloads.processes.utils import get_command_name

from .mapper import CallThroughKresMapper, MapperField, MapperPack


def v1_scheduler_safe_name(app: App):
    """the legacy app name in scheduler backend
    diff with version v2 scheduler_safe_name(current version) , version v1 have `region` as prefix"""
    return f"{app.region}-{app.scheduler_safe_name}"


class PodMapper(CallThroughKresMapper[KPod]):
    kres_class = KPod

    @property
    def pod_selector(self) -> str:
        return f"{v1_scheduler_safe_name(self.process.app)}-{self.process.name}-deployment"

    @property
    def name(self):
        return (
            f"{v1_scheduler_safe_name(self.process.app)}-{self.process.name}-"
            f"{get_command_name(self.process.runtime.proc_command)}-deployment"
        )

    @property
    def labels(self) -> dict:
        mdata = get_metadata(self.process.app)
        # module_name 将作为日志采集的标识 label，拥有 module_name 的 pod ，app_code 将是
        # paasng_app_code，而没有 module_name 的 pod，则是 engine_app.name
        # 理论上，这里的 app_code 就应该是 paasng_app_code，label 中尽量将信息拆散，由上层组装
        return dict(
            pod_selector=self.pod_selector,
            release_version=str(self.process.version),
            app_code=mdata.get_paas_app_code(),
            region=self.process.app.region,
            env=mdata.environment,
            module_name=mdata.module_name,
            process_id=self.process.name,
            # mark deployment as bkapp, maybe we will have other category in the future.
            category="bkapp",
            mapper_version="v1",
        )

    @property
    def match_labels(self) -> dict:
        return dict(
            pod_selector=self.pod_selector,
        )


class DeploymentMapper(CallThroughKresMapper[KDeployment]):
    kres_class = KDeployment

    @property
    def pod_selector(self) -> str:
        return f"{v1_scheduler_safe_name(self.process.app)}-{self.process.name}-deployment"

    @property
    def labels(self) -> dict:
        return dict(
            pod_selector=self.pod_selector,
            release_version=str(self.process.version),
        )

    @property
    def match_labels(self) -> dict:
        return dict(
            pod_selector=self.pod_selector,
        )

    @property
    def name(self) -> str:
        return (
            f"{v1_scheduler_safe_name(self.process.app)}-{self.process.name}-"
            f"{get_command_name(self.process.runtime.proc_command)}-deployment"
        )


class ReplicaSetMapper(CallThroughKresMapper[KReplicaSet]):
    kres_class = KReplicaSet

    @property
    def pod_selector(self) -> str:
        return f"{v1_scheduler_safe_name(self.process.app)}-{self.process.name}-deployment"

    @property
    def name(self) -> str:
        return (
            f"{v1_scheduler_safe_name(self.process.app)}-{self.process.name}-"
            f"{get_command_name(self.process.runtime.proc_command)}-deployment"
        )

    @property
    def match_labels(self) -> dict:
        return dict(pod_selector=self.pod_selector)


class V1Mapper(MapperPack):
    version = "v1"
    pod: MapperField[KPod] = MapperField(PodMapper)
    deployment: MapperField[KDeployment] = MapperField(DeploymentMapper)
    replica_set: MapperField[KReplicaSet] = MapperField(ReplicaSetMapper)
