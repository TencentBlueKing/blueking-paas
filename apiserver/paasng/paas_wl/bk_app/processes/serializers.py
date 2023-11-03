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
#########################
# Serializers & Readers #
#########################
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

import cattr
from django.conf import settings
from kubernetes.dynamic import ResourceField, ResourceInstance

from paas_wl.bk_app.applications.constants import WlAppType
from paas_wl.bk_app.applications.models import Release, WlApp
from paas_wl.bk_app.processes.constants import PROCESS_MAPPER_VERSION_KEY, PROCESS_NAME_KEY
from paas_wl.bk_app.processes.exceptions import UnknownProcessTypeError
from paas_wl.infras.cluster.utils import get_cluster_by_app
from paas_wl.infras.resource_templates.logging import get_app_logging_volume, get_app_logging_volume_mounts
from paas_wl.infras.resource_templates.utils import AddonManager, ProcessProbeManager
from paas_wl.infras.resources.kube_res.base import AppEntityDeserializer, AppEntitySerializer
from paas_wl.utils.kubestatus import HealthStatus, HealthStatusType, check_pod_health_status, parse_pod
from paas_wl.workloads.release_controller.constants import ImagePullPolicy

if TYPE_CHECKING:
    from paas_wl.bk_app.processes.entities import Instance, Process
    from paas_wl.infras.resources.generation.mapper import MapperPack


def extract_type_from_name(name: str, namespace: str) -> Optional[str]:
    """Extract process type from Pod/Deployment name. This function exists for compatibility reasons.

    While each deployment has a `process_id` label defined in `pod.metadata.labels`, in older version, the
    label does not exists, so the only way is extracting process_type from resource name.
    """
    try:
        return name.split(namespace)[-1].split("-")[1]
    except IndexError:
        return None


class ProcessDeserializer(AppEntityDeserializer['Process']):
    """Deserializer for Process"""

    def deserialize(self, app: WlApp, kube_data: ResourceInstance) -> 'Process':
        """Get meta info from pod template
        :param app: workloads app
        :param kube_data: k8s Deployment
        :return: Process
        """
        if app.type == WlAppType.DEFAULT:
            process = self._deserialize_for_default_app(app, kube_data)
        else:
            process = self._deserialize_for_cnative_app(app, kube_data)

        # failed should never be negative
        process.fulfill_runtime(
            replicas=kube_data.spec.replicas,
            success=kube_data.status.get('availableReplicas') or 0,
            metadata=kube_data.metadata,
        )

        return process

    def _deserialize_for_default_app(self, app: WlApp, kube_data: ResourceInstance) -> 'Process':
        """deserialize process info for default type(Heroku) app"""
        from paas_wl.bk_app.processes.entities import Resources, Runtime, Schedule

        main_container = self._get_main_container(app, kube_data)
        pod_spec = kube_data.spec.template.spec
        pod_labels = kube_data.spec.template.metadata.labels
        version = int(pod_labels.get('release_version', 0))
        process_type = self._get_process_type(kube_data)

        try:
            release = Release.objects.get_by_version(app, version=version)
            proc_command = release.get_procfile()[process_type]
        except (KeyError, Release.DoesNotExist):
            proc_command = ""

        process = self.entity_type(
            app=app,
            type=process_type,
            name=kube_data.metadata.name,
            version=version,
            replicas=kube_data.spec.replicas,
            runtime=cattr.structure(
                {
                    "envs": {env.name: env.value for env in main_container.env if getattr(env, "value", None)},
                    "image": main_container.image,
                    "command": getattr(main_container, "command", []),
                    "args": getattr(main_container, "args", []),
                    "proc_command": proc_command,
                    "image_pull_policy": getattr(main_container, "imagePullPolicy", ImagePullPolicy.IF_NOT_PRESENT),
                    "image_pull_secrets": getattr(pod_spec, "imagePullSecrets", []),
                },
                Runtime,
            ),
            schedule=cattr.structure(
                {
                    "cluster_name": get_cluster_by_app(app).name,
                    "tolerations": getattr(pod_spec, "tolerations", []),
                    "node_selector": getattr(pod_spec, "nodeSelector", {}),
                },
                Schedule,
            ),
            resources=cattr.structure(getattr(main_container, "resources", None), Resources),
        )
        return process

    def _deserialize_for_cnative_app(self, app: WlApp, kube_data: ResourceInstance) -> 'Process':
        """deserialize process info for cloud native type app"""
        from paas_wl.bk_app.processes.entities import Runtime, Schedule

        main_container = self._get_main_container(app, kube_data)
        process = self.entity_type(
            app=app,
            name=self._get_process_type(kube_data),
            version=0,
            replicas=kube_data.spec.replicas,
            type=self._get_process_type(kube_data),
            schedule=Schedule(
                cluster_name=app.latest_config.cluster,
                # TODO: 从 pod template 解析这些属性?
                tolerations=[],
                node_selector={},
            ),
            runtime=Runtime(
                # TODO: 从 pod template 解析 env
                envs={},
                image=main_container.image,
                command=getattr(main_container, "command", []),
                args=getattr(main_container, "args", []),
                image_pull_policy=main_container.imagePullPolicy,
            ),
        )
        return process

    @staticmethod
    def _get_process_type(deployment: ResourceInstance) -> str:
        """Get process type for deployment resource

        :raises: UnknownProcessTypeError: when no process_type info can be found
        """
        process_type = deployment.spec.template.metadata.labels.get(PROCESS_NAME_KEY)
        if process_type:
            return process_type

        # label `process_id` is deprecated, should use `PROCESS_NAME_KEY` instead
        process_type = deployment.spec.template.metadata.labels.get('process_id')
        if process_type:
            return process_type

        process_type = extract_type_from_name(deployment.metadata.name, deployment.metadata.namespace)
        if process_type:
            return process_type

        raise UnknownProcessTypeError(res=deployment, msg="'No process_type found in resource")

    def _get_main_container(self, app: WlApp, deployment: ResourceInstance) -> ResourceField:
        """Get main container from main Pod"""
        process_type = self._get_process_type(deployment)
        pod_template = deployment.spec.template
        for c in pod_template.spec.containers:
            if c.name == app.scheduler_safe_name_with_region:
                return c

            if c.name == process_type:
                return c
        raise RuntimeError("No main container found in resource")


class InstanceDeserializer(AppEntityDeserializer['Instance']):
    """Deserializer for Instance"""

    def deserialize(self, app: WlApp, kube_data: ResourceInstance) -> 'Instance':
        """Generate a ProcInstance by given Pod object"""
        pod = kube_data
        health_status = check_pod_health_status(parse_pod(kube_data))
        instance_state, state_message = self.parse_instance_state(pod.status.phase, health_status)

        # Use first container's status
        c_status = None
        if pod.status.get('containerStatuses'):
            c_status = pod.status.containerStatuses[0]

        process_type = self.get_process_type(pod)
        target_container = self._get_main_container(app, pod)

        envs = {}
        if target_container and hasattr(target_container, "env"):
            for env in target_container.env:
                name = getattr(env, "name", None)
                value = getattr(env, "value", None)
                if name and value is not None:
                    envs[name] = value

        return self.entity_type(
            app=app,
            name=pod.metadata.name,
            process_type=process_type,
            host_ip=pod.status.get('hostIP', None),
            start_time=pod.status.get('startTime', None),
            state=instance_state,
            state_message=state_message,
            image=target_container.image if target_container else "",
            envs=envs,
            ready=health_status.status == HealthStatusType.HEALTHY,
            restart_count=c_status.restartCount if c_status else 0,
            version=int(pod.metadata.labels.get('release_version', 0)),
        )

    def _get_main_container(self, app: WlApp, pod_info: ResourceInstance) -> Optional[ResourceField]:
        process_type = self.get_process_type(pod_info)
        for c in pod_info.spec.containers:
            if c.name == app.scheduler_safe_name_with_region:
                return c

            if c.name == process_type:
                return c
        return None

    @staticmethod
    def get_process_type(pod: ResourceInstance) -> str:
        """Get process type for pod resource

        :raises: UnknownProcessTypeError: when no process_type info can be found
        """
        labels = getattr(pod.metadata, "labels", {})
        process_type = labels.get(PROCESS_NAME_KEY)
        if process_type:
            return process_type

        # label `process_id` is deprecated, should use `PROCESS_NAME_KEY` instead
        process_type = labels.get('process_id')
        if process_type:
            return process_type

        process_type = extract_type_from_name(pod.metadata.name, pod.metadata.namespace)
        if process_type:
            return process_type

        raise UnknownProcessTypeError(res=pod, msg="No process_type found in resource")

    @staticmethod
    def parse_instance_state(pod_phase: str, health_status: HealthStatus) -> Tuple[str, str]:
        if health_status.status == HealthStatusType.UNHEALTHY:
            return health_status.reason or "Failed", health_status.message
        elif health_status.status == HealthStatusType.PROGRESSING:
            return "Pending", health_status.message
        elif health_status.status == HealthStatusType.HEALTHY:
            if pod_phase == "Succeeded":
                return "Succeeded", health_status.message
            return "Running", health_status.message
        return health_status.reason or "Unknown", health_status.message


class ProcessSerializer(AppEntitySerializer['Process']):
    """Serializer for process"""

    def serialize(self, obj: 'Process', original_obj: Optional[ResourceInstance] = None, **kwargs) -> Dict:
        mapper_version: Optional['MapperPack'] = kwargs.get("mapper_version")
        if mapper_version is None:
            raise ValueError("mapper_version is required")

        deployment_body: Dict[str, Any] = {
            'metadata': {
                'labels': mapper_version.deployment(process=obj).labels,
                'name': obj.name,
                'annotations': {PROCESS_MAPPER_VERSION_KEY: mapper_version.version},
            },
            'spec': {
                'revisionHistoryLimit': settings.MAX_RS_RETAIN,
                # add rolling update strategy to avoid 502 when redeploy or rolling update app
                'strategy': {
                    'type': 'RollingUpdate',
                    'rollingUpdate': {
                        'maxUnavailable': 0,
                        # speed up for those processes which own multiple replicas
                        'maxSurge': '75%',
                    },
                },
                'selector': {'matchLabels': mapper_version.deployment(process=obj).match_labels},
                'minReadySeconds': 1,
                'template': {
                    'spec': self._construct_pod_body_specs(obj),
                    'metadata': {
                        'labels': mapper_version.pod(process=obj).labels,
                        'name': mapper_version.pod(process=obj).name,
                    },
                },
                'replicas': obj.replicas,
            },
            'apiVersion': self.get_apiversion(),
            'kind': 'Deployment',
        }
        return deployment_body

    def _construct_pod_body_specs(self, process: 'Process') -> Dict:
        addon_mgr = AddonManager(process.app)
        process_probe_mgr = ProcessProbeManager(app=process.app, process_type=process.type)
        readiness_probe = cattr.unstructure(process_probe_mgr.get_readiness_probe())
        if readiness_probe is None and process.type == "web":
            readiness_probe = cattr.unstructure(addon_mgr.get_readiness_probe())
        liveness_probe = cattr.unstructure(process_probe_mgr.get_liveness_probe())
        startup_probe = cattr.unstructure(process_probe_mgr.get_startup_probe())
        main_container = {
            'env': [{"name": str(key), "value": str(value)} for key, value in process.runtime.envs.items()],
            # add preStop to avoid 502 when redeploy or rolling update app
            'lifecycle': {'pre_stop': {'_exec': {'command': ["sleep", "15"]}}},
            'image': process.runtime.image,
            # TODO: 与 cnative 应用统一主容器名字
            'name': process.main_container_name,
            'command': process.runtime.command,
            'args': process.runtime.args,
            'imagePullPolicy': process.runtime.image_pull_policy,
            'resources': {
                'limits': process.resources.limits if process.resources else {},
                'requests': process.resources.requests if process.resources else {},
            },
            # TODO: 重构「主入口」时, 允许用户自行填写 containerPort
            'ports': [{'containerPort': settings.CONTAINER_PORT}],
            'volumeMounts': cattr.unstructure(
                get_app_logging_volume_mounts(process.app) + addon_mgr.get_volume_mounts()
            ),
            'readinessProbe': readiness_probe,
            'livenessProbe': liveness_probe,
            'startupProbe': startup_probe,
        }

        return {
            'containers': [main_container] + cattr.unstructure(addon_mgr.get_sidecars()),
            'volumes': cattr.unstructure(get_app_logging_volume(process.app) + addon_mgr.get_volumes()),
            'imagePullSecrets': process.runtime.image_pull_secrets,
            'nodeSelector': process.schedule.node_selector or None,
            'tolerations': process.schedule.tolerations or None,
            # 不默认向 Pod 中挂载 ServiceAccount Token
            'automountServiceAccountToken': False,
        }
