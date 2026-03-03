# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
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

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union

from kubernetes.dynamic import ResourceInstance

from paas_wl.bk_app.applications.constants import WlAppType
from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.processes.constants import PROCESS_NAME_KEY
from paas_wl.infras.resources.kube_res.base import AppEntityDeserializer, AppEntitySerializer
from paas_wl.workloads.autoscaling.constants import (
    GPA_COMPUTE_BY_LIMITS_ANNO_KEY,
    ScalingMetric,
    ScalingMetricName,
    ScalingMetricSourceType,
    ScalingMetricTargetType,
)
from paas_wl.workloads.autoscaling.entities import MetricSpec, ProcAutoscalingSpec, ScalingObjectRef

if TYPE_CHECKING:
    from paas_wl.workloads.autoscaling.kres_entities import ProcAutoscaling


class ProcAutoscalingDeserializer(AppEntityDeserializer["ProcAutoscaling", "WlApp"]):
    """Deserializer for ProcAutoscaling"""

    def deserialize(self, app: WlApp, kube_data: ResourceInstance) -> "ProcAutoscaling":
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
            raise ValueError("unsupported app type: {}".format(app.type))

        return proc_autoscaling

    def _deserialize_for_default_app(self, app: WlApp, kube_data: ResourceInstance) -> "ProcAutoscaling":
        """deserialize process auto scaling config for default type(Heroku) app"""
        return self.entity_type(
            app=app,
            name=kube_data.metadata.name,
            spec=ProcAutoscalingSpec(
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

    def _deserialize_for_cnative_app(self, app: WlApp, kube_data: ResourceInstance) -> "ProcAutoscaling":
        """deserialize process auto scaling config for cloud native type app"""
        raise NotImplementedError("work in progress")

    def _parse_metrics(self, gpa: ResourceInstance) -> List[MetricSpec]:
        """Parse metrics for general pod autoscaler resource"""
        metrics: List[MetricSpec] = []
        for m in gpa.spec.metric.metrics:
            # TODO 目前 MetricSource 只支持 Resources，需要支持 Pods & Object
            if m.type != ScalingMetricSourceType.RESOURCE:
                raise ValueError("unsupported metric source type: {}".format(m.type))

            metrics.append(
                MetricSpec(
                    type=m.type,
                    metric=self._get_metric(m.resource.name, m.resource.target.type),
                    value=self._get_metric_value(m.resource.target),
                )
            )

        return metrics

    def _get_metric(self, res_name: str, target_type: str) -> ScalingMetric:
        """获取 metric name"""
        type_name_metric_map: Dict[Tuple[str, str], ScalingMetric] = {
            (ScalingMetricTargetType.UTILIZATION, ScalingMetricName.CPU): ScalingMetric.CPU_UTILIZATION,
            (ScalingMetricTargetType.UTILIZATION, ScalingMetricName.MEMORY): ScalingMetric.MEMORY_UTILIZATION,
            (ScalingMetricTargetType.AVERAGE_VALUE, ScalingMetricName.CPU): ScalingMetric.CPU_AVERAGE_VALUE,
            (ScalingMetricTargetType.AVERAGE_VALUE, ScalingMetricName.MEMORY): ScalingMetric.MEMORY_AVERAGE_VALUE,
        }

        if (target_type, res_name) not in type_name_metric_map:
            raise ValueError(f"unsupported metric res_name {res_name} and target type: {target_type}")

        return type_name_metric_map[(target_type, res_name)]

    def _get_metric_value(self, metric_target: Dict[str, Union[str, int]]) -> str:
        """将 gpa 配置中的 averageValue/averageUtilization 转换为统一的数值"""
        metric_type = metric_target["type"]
        if metric_type == ScalingMetricTargetType.UTILIZATION:
            return str(metric_target["averageUtilization"])

        if metric_type == ScalingMetricTargetType.AVERAGE_VALUE:
            return str(metric_target["averageValue"])

        raise ValueError("unsupported metric type: {}".format(metric_type))


class ProcAutoscalingSerializer(AppEntitySerializer["ProcAutoscaling"]):
    """Serializer for process auto scaling"""

    api_version = "autoscaling.tkex.tencent.com/v1alpha1"

    def serialize(self, obj: "ProcAutoscaling", original_obj: Optional[ResourceInstance] = None, **kwargs) -> Dict:
        manifest: Dict[str, Any] = {
            "apiVersion": self.get_apiversion(),
            "kind": obj.Meta.kres_class.kind,
            "metadata": {
                "namespace": obj.app.namespace,
                "name": obj.name,
                "annotations": {
                    PROCESS_NAME_KEY: obj.name,
                    GPA_COMPUTE_BY_LIMITS_ANNO_KEY: "true",
                },
            },
            "spec": {
                "minReplicas": obj.spec.min_replicas,
                "maxReplicas": obj.spec.max_replicas,
                "scaleTargetRef": {
                    "apiVersion": obj.target_ref.api_version,
                    "kind": obj.target_ref.kind,
                    "name": obj.target_ref.name,
                },
                "metric": {
                    "metrics": [
                        # TODO 目前 MetricSource 只支持 Resources，需要支持 Pods & Object
                        {"type": "Resource", "resource": self._gen_resource_metric_source(metric)}
                        for metric in obj.spec.metrics
                    ]
                },
            },
        }
        return manifest

    @staticmethod
    def _gen_resource_metric_source(spec: "MetricSpec") -> Dict[str, Any]:
        """
        根据指定的指标信息，生成对应的 k8s ResourceMetricSource

        CPU 绝对数值 -> {"name": "cpu", "target": {"type": "AverageValue", "averageValue": "1000m"}}
        内存 绝对数值 -> {"name": "memory", "target": {"type": "AverageValue", "averageValue": "512Mi"}}
        CPU 使用率百分比 -> {"name": "cpu", "target": {"type": Utilization, "averageUtilization": 80}}
        """
        value: Union[str, int]
        if spec.metric == ScalingMetric.CPU_UTILIZATION:
            metric_name, target_type = ScalingMetricName.CPU, ScalingMetricTargetType.UTILIZATION
            value_key, value = "averageUtilization", int(spec.value)

        elif spec.metric == ScalingMetric.MEMORY_UTILIZATION:
            metric_name, target_type = ScalingMetricName.MEMORY, ScalingMetricTargetType.UTILIZATION
            value_key, value = "averageUtilization", int(spec.value)

        elif spec.metric == ScalingMetric.CPU_AVERAGE_VALUE:
            metric_name, target_type = ScalingMetricName.CPU, ScalingMetricTargetType.AVERAGE_VALUE
            value_key, value = "averageValue", spec.value

        elif spec.metric == ScalingMetric.MEMORY_AVERAGE_VALUE:
            metric_name, target_type = ScalingMetricName.MEMORY, ScalingMetricTargetType.AVERAGE_VALUE
            value_key, value = "averageValue", spec.value

        else:
            raise ValueError("unsupported metric: {}".format(spec.metric))

        return {"name": metric_name.value, "target": {"type": target_type.value, value_key: value}}
