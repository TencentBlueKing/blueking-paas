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
import logging
from typing import Dict
from unittest import mock

import pytest

from paas_wl.cnative.specs.constants import (
    IMAGE_CREDENTIALS_REF_ANNO_KEY,
    DeployStatus,
    MResConditionType,
    MResPhaseType,
)
from paas_wl.cnative.specs.credentials import ImageCredentialsManager
from paas_wl.cnative.specs.resource import MresConditionParser, deploy, get_mres_from_cluster
from paas_wl.platform.applications.models import EngineApp
from paas_wl.resources.utils.basic import get_client_by_env
from paas_wl.workloads.images.constants import KUBE_RESOURCE_NAME as PULL_SECRET_NAME
from tests.cnative.specs.utils import create_condition, create_res_with_conds
from tests.utils.mocks.platform import FakePlatformSvcClient

pytestmark = pytest.mark.django_db
logger = logging.getLogger(__name__)


class TestMresConditionDetector:
    @pytest.mark.parametrize(
        "mres, expected_status",
        [
            (create_res_with_conds([]), DeployStatus.PENDING),
            (
                create_res_with_conds([create_condition(MResConditionType.APP_AVAILABLE)]),
                DeployStatus.PROGRESSING,
            ),
            (
                create_res_with_conds(
                    [create_condition(MResConditionType.APP_AVAILABLE, "True")], MResPhaseType.AppRunning
                ),
                DeployStatus.READY,
            ),
            (
                create_res_with_conds(
                    [create_condition(MResConditionType.ADDONS_PROVISIONED, "False")], MResPhaseType.AppFailed
                ),
                DeployStatus.ERROR,
            ),
            (
                create_res_with_conds(
                    [
                        create_condition(MResConditionType.ADDONS_PROVISIONED, "False"),
                        create_condition(MResConditionType.APP_AVAILABLE, "True"),
                    ],
                    MResPhaseType.AppFailed,
                ),
                DeployStatus.READY,
            ),
        ],
    )
    def test_detect(self, mres, expected_status):
        s = MresConditionParser(mres).detect_state()
        assert s.status == expected_status


@pytest.mark.skip_when_no_crds
class TestBkAppClusterOperator:
    """测试在集群中操作 bkapp 资源"""

    @pytest.fixture(autouse=True)
    def _setup_clients(self):
        with mock.patch('paas_wl.platform.external.client._global_plat_client', new=FakePlatformSvcClient()):
            yield

    def test_deploy_and_get_status(self, bk_app, bk_stag_env):
        manifest: Dict = {
            "apiVersion": "paas.bk.tencent.com/v1alpha1",
            "kind": "BkApp",
            "metadata": {"name": bk_app.code, "annotations": {IMAGE_CREDENTIALS_REF_ANNO_KEY: "true"}},
            "spec": {
                "processes": [
                    {"name": "web", "replicas": 1, "image": "nginx:latest", "cpu": "100m", "memory": "100Mi"}
                ],
                "hooks": {"preRelease": {"command": ["/bin/echo"], "args": ["Hello"]}},
                "configuration": {"env": []},
            },
        }

        # Don't wait for controller
        with mock.patch('paas_wl.cnative.specs.resource.KNamespace.wait_for_default_sa'):
            ret = deploy(bk_stag_env, manifest)

        assert ret["spec"]["processes"][0]["name"] == "web"
        assert get_mres_from_cluster(bk_stag_env) is not None

        engine_app = EngineApp.objects.get_by_env(bk_stag_env)
        with get_client_by_env(bk_stag_env) as client:
            assert ImageCredentialsManager(client).get(engine_app, PULL_SECRET_NAME) is not None

        # 修改进程配置信息，再次部署到集群
        manifest["spec"]["processes"].append(
            {"name": "worker", "replicas": 1, "image": "busybox:latest", "cpu": "100m", "memory": "100Mi"}
        )
        ret = deploy(bk_stag_env, manifest)
        assert ret["spec"]["processes"][1]["name"] == "worker"
