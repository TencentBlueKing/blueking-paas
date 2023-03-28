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
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from kubernetes.dynamic import ResourceInstance
from kubernetes.utils import parse_quantity

from paas_wl.platform.applications.constants import WlAppType
from paas_wl.platform.applications.models import Release, WlApp
from paas_wl.resources.base.kres import KDeployment
from paas_wl.resources.kube_res.base import AppEntityDeserializer, AppEntitySerializer, GVKConfig
from paas_wl.resources.utils.basic import get_client_by_app
from paas_wl.workloads.autoscaling.constants import ScalingMetricName, ScalingMetricSourceType, ScalingMetricType
from paas_wl.workloads.autoscaling.exceptions import AutoScalingUnsupported
from paas_wl.workloads.autoscaling.models import ScalingConfig, ScalingMetric
from paas_wl.workloads.processes.constants import PROCESS_NAME_KEY
from paas_wl.workloads.processes.models import Process
from paas_wl.workloads.processes.serializers import ProcessSerializer

if TYPE_CHECKING:
    from paas_wl.workloads.autoscaling.entities import ProcAutoScaling


class ProcAutoScalingDeserializer(AppEntityDeserializer['ProcAutoScaling']):
    """Deserializer for ProcAutoScaling"""

    def deserialize(self, app: WlApp, kube_data: ResourceInstance) -> 'ProcAutoScaling':
        """Get scaling config from gpa spec

        :param app: workloads app
        :param kube_data: k8s GPA
        :return: ProcAutoScaling
        """
        if app.type == WlAppType.DEFAULT:
            proc_auto_scaling = self._deserialize_for_default_app(app, kube_data)
        elif app.type == WlAppType.CLOUD_NATIVE:
            proc_auto_scaling = self._deserialize_for_cnative_app(app, kube_data)
        else:
            raise ValueError('unsupported app type: {}'.format(app.type))

        return proc_auto_scaling

    def _deserialize_for_default_app(self, app: WlApp, kube_data: ResourceInstance) -> 'ProcAutoScaling':
        """deserialize process auto scaling config for default type(Heroku) app"""
        return self.entity_type(
            app=app,
            name=self._get_process_type(kube_data),
            spec=ScalingConfig(
                min_replicas=kube_data.spec.minReplicas,
                max_replicas=kube_data.spec.maxReplicas,
                metrics=self._parse_metrics(kube_data),
            ),
        )

    def _deserialize_for_cnative_app(self, app: WlApp, kube_data: ResourceInstance) -> 'ProcAutoScaling':
        """deserialize process auto scaling config for cloud native type app"""
        raise NotImplementedError('work in progress')

    @staticmethod
    def _get_process_type(gpa: ResourceInstance) -> str:
        """Get process type for general pod autoscaler resource"""
        process_type = gpa.metadata.annotations.get(PROCESS_NAME_KEY)
        if process_type:
            return process_type

        # 如果 gpa 的注解中没有 PROCESS_NAME_KEY，则通过 gpa 的名称来解析出 process_type
        return gpa.metadata.name.split('-')[-1]

    def _parse_metrics(self, gpa: ResourceInstance) -> List[ScalingMetric]:
        """Parse metrics for general pod autoscaler resource"""
        metrics: List[ScalingMetric] = []
        for metric in gpa.spec.metric.metrics:
            # 目前只有 ResourcesMetricSource，不支持其他类型的 metric
            if metric.type != ScalingMetricSourceType.RESOURCE:
                raise ValueError('unsupported metric source type: {}'.format(metric.type))

            metric.append(
                ScalingMetric(
                    name=metric.resource.name,
                    type=metric.resource.target.type,
                    value=self._parse_metric_value(metric.resource.target, metric.resource.name),
                )
            )

        return metrics

    def _parse_metric_value(self, metric_target: Dict[str, Union[str, int]], metric_name: ScalingMetricName) -> int:
        """将 gpa 配置中的 averageValue/averageUtilization 转换为统一的数值"""
        if metric_target['type'] == ScalingMetricType.UTILIZATION:
            return int(metric_target['averageUtilization'])

        elif metric_target['type'] == ScalingMetricType.AVERAGE_VALUE:
            return self._parse_average_value(str(metric_target['averageValue']), metric_name)

        raise ValueError('unsupported metric type: {}'.format(metric_target['type']))

    @staticmethod
    def _parse_average_value(raw_val: str, metric_name: ScalingMetricName) -> int:
        """将 gpa 配置中的 averageValue 去除单位做转换
        例如：1000m, cpu -> 1000, 512Mi, memory -> 512
        """
        if metric_name == ScalingMetricName.CPU:
            return int(parse_quantity(raw_val) * 1000)

        if metric_name == ScalingMetricName.MEMORY:
            return int(parse_quantity(raw_val) / (1024 * 1024))

        raise ValueError('unsupported metric name: {}'.format(metric_name))


class ProcAutoScalingSerializer(AppEntitySerializer['ProcAutoScaling']):
    """Serializer for process auto scaling"""

    api_version = 'autoscaling.tkex.tencent.com/v1alpha1'

    def get_res_name(self, obj: 'ProcAutoScaling', **kwargs) -> str:
        """根据规则，生成 GPA 资源名称"""
        return f"{obj.app.scheduler_safe_name}--{obj.name}"

    def serialize(self, obj: 'ProcAutoScaling', original_obj: Optional[ResourceInstance] = None, **kwargs) -> Dict:
        manifest: Dict[str, Any] = {
            'apiVersion': self.get_apiversion(),
            'kind': obj.Meta.kres_class.kind,
            'metadata': {'name': self.get_res_name(obj), 'annotations': {PROCESS_NAME_KEY: obj.name}},
            'spec': {
                'minReplicas': obj.spec.min_replicas,
                'maxReplicas': obj.spec.max_replicas,
                'scaleTargetRef': self._gen_scale_target_ref(obj, **kwargs),
                'metric': {
                    'metrics': [
                        {'type': 'Resource', 'resource': self._gen_resource_metric_source(metric)}
                        for metric in obj.spec.metrics
                    ]
                },
            },
        }
        return manifest

    @staticmethod
    def _gen_resource_metric_source(metric: 'ScalingMetric') -> Dict[str, Any]:
        """
        根据指定的指标信息，生成对应的 k8s ResourceMetricSource

        :returns:
        CPU 绝对数值 -> {"name": "cpu", "target": {"type": "AverageValue", "averageValue": "1000m"}}
        内存 绝对数值 -> {"name": "memory", "target": {"type": "AverageValue", "averageValue": "512Mi"}}
        CPU 使用率百分比 -> {"name": "cpu", "target": {"type": Utilization, "averageUtilization": 80}}
        """
        if metric.type == ScalingMetricType.UTILIZATION:
            # 资源使用率百分比
            value_key, value = 'averageUtilization', metric.value
        elif metric.type == ScalingMetricType.AVERAGE_VALUE:
            # 资源使用绝对数值
            value_key = 'averageValue'
            value_tmpl = '{}m' if metric.name == ScalingMetricName.CPU else '{}Mi'
            value = value_tmpl.format(metric.value)  # type: ignore
        else:
            raise ValueError('unsupported metric type: {}'.format(metric.type))

        return {'name': metric.name, 'target': {'type': metric.type, value_key: value}}

    @staticmethod
    def _gen_scale_target_ref(obj: 'ProcAutoScaling', **kwargs) -> Dict[str, str]:
        """生成 GPA 控制的资源信息"""
        # 普通应用只有成功部署过，才能设置自动扩缩容
        try:
            release = Release.objects.get_latest(obj.app, ignore_failed=True)
        except Release.DoesNotExist:
            raise AutoScalingUnsupported("autoscaling can't be used because no successful release found.")

        with get_client_by_app(obj.app) as client:
            kres_client = KDeployment(client, api_version='')
            gvk_config = GVKConfig(
                server_version=kres_client.version['kubernetes']['gitVersion'],
                kind=kres_client.kind,
                preferred_apiversion=kres_client.get_preferred_version(),
                available_apiversions=kres_client.get_available_versions(),
            )

        proc = Process.from_release(obj.name, release)
        proc_slz = ProcessSerializer(Process, gvk_config=gvk_config)
        return {
            'apiVersion': proc_slz.get_apiversion(),
            'kind': Process.Meta.kres_class.kind,
            'name': proc_slz.get_res_name(proc, **kwargs),
        }
