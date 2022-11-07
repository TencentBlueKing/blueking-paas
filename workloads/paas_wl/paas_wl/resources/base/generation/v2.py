# -*- coding: utf-8 -*-
from paas_wl.platform.applications.models.managers.app_metadata import get_metadata
from paas_wl.resources.base.kres import KDeployment, KPod, KReplicaSet
from paas_wl.utils.basic import digest_if_length_exceeded

from .mapper import CallThroughKresMapper, MapperField, MapperPack


class PodMapper(CallThroughKresMapper[KPod]):
    kres_class = KPod

    @property
    def name(self) -> str:
        return f"{self.process.app.scheduler_safe_name}--{self.process.name}"

    @property
    def pod_selector(self) -> str:
        return digest_if_length_exceeded(f"{self.process.app.name}-{self.process.name}", 63)

    @property
    def labels(self) -> dict:
        mdata = get_metadata(self.process.app)
        return dict(
            pod_selector=self.pod_selector,
            release_version=str(self.process.version),
            app_code=mdata.get_paas_app_code(),
            region=self.process.app.region,
            env=mdata.environment,
            module_name=mdata.module_name,
            process_id=self.process.name,
            category="bkapp",
            mapper_version="v2",
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
        return digest_if_length_exceeded(f"{self.process.app.name}-{self.process.name}", 63)

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
        return f"{self.process.app.scheduler_safe_name}--{self.process.name}"


class ReplicaSetMapper(CallThroughKresMapper[KReplicaSet]):
    kres_class = KReplicaSet

    @property
    def pod_selector(self) -> str:
        return digest_if_length_exceeded(f"{self.process.app.name}-{self.process.name}", 63)

    @property
    def name(self) -> str:
        return f"{self.process.app.name.replace('_', '0us0')}--{self.process.name}"

    @property
    def match_labels(self) -> dict:
        return dict(
            pod_selector=self.pod_selector,
        )


class V2Mapper(MapperPack):
    version = "v2"
    _ignore_command_name = True
    pod: MapperField[KPod] = MapperField(PodMapper)
    deployment: MapperField[KDeployment] = MapperField(DeploymentMapper)
    replica_set: MapperField[KReplicaSet] = MapperField(ReplicaSetMapper)
