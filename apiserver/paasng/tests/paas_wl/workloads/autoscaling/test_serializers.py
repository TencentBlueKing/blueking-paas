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
from typing import Any, Dict

import pytest
from kubernetes.dynamic import ResourceInstance

from paas_wl.resources.base import crd
from paas_wl.resources.base.generation import get_mapper_version
from paas_wl.resources.kube_res.base import GVKConfig
from paas_wl.workloads.autoscaling.constants import ScalingMetricName, ScalingMetricType
from paas_wl.workloads.autoscaling.entities import ProcAutoscaling
from paas_wl.workloads.autoscaling.models import AutoscalingConfig, AutoscalingTargetRef, ScalingMetric
from paas_wl.workloads.autoscaling.serializers import ProcAutoscalingDeserializer, ProcAutoscalingSerializer
from paas_wl.workloads.processes.models import Process

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture
def gpa_gvk_config():
    return GVKConfig(
        server_version='1.20',
        kind=crd.GPA.kind,
        preferred_apiversion=ProcAutoscalingSerializer.api_version,
        available_apiversions=[ProcAutoscalingSerializer.api_version],
    )


@pytest.fixture
def gpa_manifest() -> Dict[str, Any]:
    return {
        'apiVersion': 'autoscaling.tkex.tencent.com/v1alpha1',
        'kind': 'GeneralPodAutoscaler',
        'metadata': {
            'name': 'bkapp-xx123-stag--web',
            'annotations': {
                'bkapp.paas.bk.tencent.com/process-name': 'web',
            },
        },
        'spec': {
            'minReplicas': 2,
            'maxReplicas': 5,
            'scaleTargetRef': {
                'apiVersion': 'apps/v1',
                'kind': 'Deployment',
                'name': 'bkapp-xx123-stag--web',
            },
            'metric': {
                'metrics': [
                    {
                        'type': 'Resource',
                        'resource': {'name': 'cpu', 'target': {'type': 'AverageValue', 'averageValue': '1000m'}},
                    },
                    {
                        'type': 'Resource',
                        'resource': {
                            'name': 'memory',
                            'target': {'type': 'Utilization', 'averageUtilization': 80},
                        },
                    },
                    {
                        'type': 'Resource',
                        'resource': {
                            'name': 'memory',
                            'target': {'type': 'AverageValue', 'averageValue': '256Mi'},
                        },
                    },
                ]
            },
        },
    }


@pytest.fixture
def scaling(wl_app) -> ProcAutoscaling:
    return ProcAutoscaling(
        app=wl_app,
        name='web',
        spec=AutoscalingConfig(
            min_replicas=2,
            max_replicas=5,
            metrics=[
                ScalingMetric(
                    name=ScalingMetricName.CPU,
                    type=ScalingMetricType.AVERAGE_VALUE,
                    raw_value="1000m",
                ),
                ScalingMetric(
                    name=ScalingMetricName.MEMORY,
                    type=ScalingMetricType.UTILIZATION,
                    raw_value=80,
                ),
                ScalingMetric(
                    name=ScalingMetricName.MEMORY,
                    type=ScalingMetricType.AVERAGE_VALUE,
                    raw_value="256Mi",
                ),
            ],
        ),
        target_ref=AutoscalingTargetRef(
            kind='Deployment',
            api_version='apps/v1',
            name="bkapp-xx123-stag--web",
        ),
    )


def test_ProcAutoscalingSerializer(wl_app, wl_release, gpa_gvk_config, gpa_manifest, scaling):
    process = Process.from_release(type_="web", release=wl_release)

    serializer = ProcAutoscalingSerializer(ProcAutoscaling, gpa_gvk_config)
    assert serializer.get_res_name(scaling) == f"{wl_app.scheduler_safe_name}--{process.name}"

    excepted = gpa_manifest
    excepted['metadata']['name'] = f"{wl_app.scheduler_safe_name}--{process.name}"
    excepted['metadata']['namespace'] = wl_app.namespace
    assert serializer.serialize(scaling, mapper_version=get_mapper_version(target="v2")) == excepted


def test_ProcAutoscalingDeserializer(wl_app, gpa_gvk_config, gpa_manifest, scaling):
    kube_data = ResourceInstance(None, gpa_manifest)
    assert ProcAutoscalingDeserializer(ProcAutoscaling, gpa_gvk_config).deserialize(wl_app, kube_data) == scaling
