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
import base64
import gzip
import json

import pytest
from kubernetes.dynamic import ResourceInstance

from paas_wl.admin.constants import HELM_RELEASE_SECRET_TYPE
from paas_wl.admin.helpers.helm import DeployResult, HelmChart, HelmRelease, HelmReleaseParser


@pytest.fixture
def helm_release_secret() -> ResourceInstance:
    release_data = {
        "name": "bkpaas-app-operator",
        "namespace": "blueking",
        "version": 1,
        "chart": {
            "metadata": {
                "name": "bkpaas-app-operator",
                "version": "1.1.0-beta.1",
                "description": "this is a description",
                "appVersion": "v1.1.0-beta.1",
            }
        },
        "info": {
            "status": "superseded",
            "description": "Upgrade complete",
            "last_deployed": "2023-06-29T17:25:24.359441991+08:00",
        },
        "manifest": "---\nfoo: bar\n---\nbar: boo\n",
    }
    raw = base64.b64encode(base64.b64encode(gzip.compress(json.dumps(release_data).encode())))
    return ResourceInstance(
        None,
        {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {
                "name": "sh.helm.release.v1.bkpaas-app-operator.v1",
                "namespace": "blueking",
            },
            "type": HELM_RELEASE_SECRET_TYPE,
            "data": {"release": raw},
        },
    )


def test_HelmReleaseParser(helm_release_secret):
    release = HelmReleaseParser(helm_release_secret, parse_manifest=True).parse()
    assert release == HelmRelease(
        name="bkpaas-app-operator",
        namespace="blueking",
        version=1,
        chart=HelmChart(
            name="bkpaas-app-operator",
            version="1.1.0-beta.1",
            app_version="v1.1.0-beta.1",
            description="this is a description",
        ),
        deploy_result=DeployResult(
            status="superseded",
            description="Upgrade complete",
            created_at="2023-06-29 17:25:24+08:00",
        ),
        resources=[{"foo": "bar"}, {"bar": "boo"}],
        secret_name="sh.helm.release.v1.bkpaas-app-operator.v1",
    )
