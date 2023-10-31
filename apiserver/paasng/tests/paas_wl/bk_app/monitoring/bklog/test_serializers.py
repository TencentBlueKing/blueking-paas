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

import cattrs
import pytest

from paas_wl.bk_app.monitoring.bklog.entities import BkAppLogConfig
from paas_wl.bk_app.monitoring.bklog.models import LabelSelector
from paas_wl.bk_app.monitoring.bklog.serializers import BKLogConfigSerializer
from paas_wl.infras.resources.base import crd
from paas_wl.infras.resources.kube_res.base import GVKConfig

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture
def gvk_config():
    return GVKConfig(
        server_version='1.20',
        kind=crd.BKLogConfig.kind,
        preferred_apiversion=BKLogConfigSerializer.api_version,
        available_apiversions=[BKLogConfigSerializer.api_version],
    )


@pytest.fixture
def bklog_manifest(wl_app) -> Dict[str, Any]:
    return {
        "apiVersion": "bk.tencent.com/v1alpha1",
        "kind": "BkLogConfig",
        "metadata": {
            "name": "test",
            "namespace": wl_app.namespace,
            "labels": {"app.kubernetes.io/managed-by": "bk-paas3"},
        },
        "spec": {
            "addPodLabel": True,
            "namespaceSelector": {"matchNames": [wl_app.name]},
            "allContainer": False,
            "workloadType": "Deployment",
            "labelSelector": {
                "matchExpressions": [{"key": "bkapp.paas.bk.tencent.com/code", "operator": "Exists", "values": None}],
                "matchLabels": {},
            },
            "dataId": 123,
            "encoding": "utf-8",
            "path": ["/", "/foo"],
            "filters": [],
            "extMeta": {},
            "logConfigType": "container_log_config",
        },
    }


class TestBKLogConfigSerializer:
    def test_serialize(self, wl_app, gvk_config, bklog_manifest):
        slz = BKLogConfigSerializer(BkAppLogConfig, gvk_config)

        obj = BkAppLogConfig(
            app=wl_app,
            name="test",
            data_id=123,
            paths=["/", "/foo"],
            label_selector=cattrs.structure(
                {"matchExpressions": [{"key": "bkapp.paas.bk.tencent.com/code", "operator": "Exists"}]}, LabelSelector
            ),
        )
        assert slz.serialize(obj) == bklog_manifest
