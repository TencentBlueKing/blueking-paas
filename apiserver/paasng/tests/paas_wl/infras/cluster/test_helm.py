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

from pathlib import Path

import pytest
import yaml
from kubernetes.dynamic import ResourceInstance

from paas_wl.infras.cluster.constants import HelmChartDeployStatus
from paas_wl.infras.cluster.helm import HelmReleaseParser


@pytest.fixture
def helm_release_secret() -> ResourceInstance:
    with open(Path(__file__).resolve().parent / "assets" / "helm-release-secret.yaml") as fr:
        data = yaml.safe_load(fr)

    return ResourceInstance(None, data)


class TestHelmReleaseParser:
    def test_parse(self, helm_release_secret):
        release = HelmReleaseParser(helm_release_secret).parse()
        assert release.name == "jaeger"
        assert release.namespace == "bk-jaeger"
        assert release.version == 1
        assert release.chart.name == "jaeger"
        assert release.chart.version == "2.2.1"
        assert release.chart.app_version == "1.57.0"
        assert release.deploy_result.status == HelmChartDeployStatus.DEPLOYED
        assert release.values == {"cassandra": {"persistence": {"size": "10Gi"}}}
        assert len(release.resources) == 22
        assert release.secret_name == "sh.helm.release.v1.jaeger.v1"
