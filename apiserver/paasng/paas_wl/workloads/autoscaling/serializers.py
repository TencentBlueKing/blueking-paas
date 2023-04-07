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

from paas_wl.platform.applications.constants import WlAppType
from paas_wl.platform.applications.models import WlApp
from paas_wl.resources.kube_res.base import AppEntityDeserializer, AppEntitySerializer
from paas_wl.workloads.autoscaling.constants import ScalingMetricSourceType, ScalingMetricTargetType
from paas_wl.workloads.autoscaling.models import AutoscalingConfig, ScalingMetric, ScalingObjectRef
from paas_wl.workloads.processes.constants import PROCESS_NAME_KEY

if TYPE_CHECKING:
    from paas_wl.workloads.autoscaling.entities import ProcAutoscaling


class ProcAutoscalingDeserializer(AppEntityDeserializer['ProcAutoscaling']):
    """Deserializer for ProcAutoscaling"""

    def deserialize(self, app: WlApp, kube_data: ResourceInstance) -> 'ProcAutoscaling':
        """Get scaling config from gpa spec

        :param app: workloads app
        :param kube_data: k8s GPA
        :return: ProcAutoscaling
        """
        if app.type == WlAppType.DEFAULT:
            proc_autoscaling = self._deserialize_for_default_app(app, kube_data)
        elif app.type == WlAppType.CLOUD_NATIVE:
            proc_autoscaling = self._deserialize_for_cnative_app(app, kube_data)
        else:
            raise ValueError('unsupported app type: {}'.format(app.type))

        return proc_autoscaling

    def _deserialize_for_default_app(self, app: WlApp, kube_data: ResourceInstance) -> 'ProcAutoscaling':
        """deserialize process auto scaling config for default type(Heroku) app"""
        return self.entity_type(
            app=app,
            name=kube_data.metadata.name,
            spec=AutoscalingConfig(
                min_replicas=kube_data.spec.minReplicas,
                max_replicas=kube_data.spec.maxReplicas,
                metrics=self._parse_metrics(kube_data),
            ),
            target_ref=ScalingObjectRef(
                api_version=kube_data.spec.scaleTargetRef.apiVersion,
                kind=kube_data.spec.scaleTargetRef.kind,
                name=kube_data.spec.scaleTargetRef.name,
            ),
        )

    def _deserialize_for_cnative_app(self, app: WlApp, kube_data: ResourceInstance) -> 'ProcAutoscaling':
        """deserialize process auto scaling config for cloud native type app"""
        raise NotImplementedError('work in progress')

    def _parse_metrics(self, gpa: ResourceInstance) -> List[ScalingMetric]:
        """Parse metrics for general pod autoscaler resource"""
        metrics: List[ScalingMetric] = []
        for m in gpa.spec.metric.metrics:
            # TODO 目前 MetricSource 只支持 Resources，需要支持 Pods & Object
            if m.type != ScalingMetricSourceType.RESOURCE:
                raise ValueError('unsupported metric source type: {}'.format(m.type))

            metrics.append(
                ScalingMetric(
                    type=m.type,
                    name=m.resource.name,
                    target_type=m.resource.target.type,
                    target_value=self._get_metric_value(m.resource.target),
                )
            )

        return metrics

    def _get_metric_value(self, metric_target: Dict[str, Union[str, int]]) -> str:
        """将 gpa 配置中的 averageValue/averageUtilization 转换为统一的数值"""
        metric_type = metric_target['type']
        if metric_type == ScalingMetricTargetType.UTILIZATION:
            return str(metric_target['averageUtilization'])

        if metric_type == ScalingMetricTargetType.AVERAGE_VALUE:
            return str(metric_target['averageValue'])

        raise ValueError('unsupported metric type: {}'.format(metric_type))


class ProcAutoscalingSerializer(AppEntitySerializer['ProcAutoscaling']):
    """Serializer for process auto scaling"""

    api_version = 'autoscaling.tkex.tencent.com/v1alpha1'

    def serialize(self, obj: 'ProcAutoscaling', original_obj: Optional[ResourceInstance] = None, **kwargs) -> Dict:
        manifest: Dict[str, Any] = {
            'apiVersion': self.get_apiversion(),
            'kind': obj.Meta.kres_class.kind,
            'metadata': {
                'namespace': obj.app.namespace,
                'name': obj.name,
                'annotations': {PROCESS_NAME_KEY: obj.name},
            },
            'spec': {
                'minReplicas': obj.spec.min_replicas,
                'maxReplicas': obj.spec.max_replicas,
                'scaleTargetRef': {
                    'apiVersion': obj.target_ref.api_version,
                    'kind': obj.target_ref.kind,
                    'name': obj.target_ref.name,
                },
                'metric': {
                    'metrics': [
                        # TODO 目前 MetricSource 只支持 Resources，需要支持 Pods & Object
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

        CPU 绝对数值 -> {"name": "cpu", "target": {"type": "AverageValue", "averageValue": "1000m"}}
        内存 绝对数值 -> {"name": "memory", "target": {"type": "AverageValue", "averageValue": "512Mi"}}
        CPU 使用率百分比 -> {"name": "cpu", "target": {"type": Utilization, "averageUtilization": 80}}
        """
        if metric.target_type == ScalingMetricTargetType.UTILIZATION:
            # 资源使用率百分比
            value_key, value = 'averageUtilization', int(metric.target_value)

        elif metric.target_type == ScalingMetricTargetType.AVERAGE_VALUE:
            # 资源使用绝对数值
            value_key, value = 'averageValue', metric.target_value  # type: ignore
        else:
            raise ValueError('unsupported metric target type: {}'.format(metric.target_type))

        return {'name': metric.name, 'target': {'type': metric.target_type, value_key: value}}
