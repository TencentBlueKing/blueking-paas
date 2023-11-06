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

import pytest

from paas_wl.bk_app.cnative.specs.constants import (
    IMAGE_CREDENTIALS_REF_ANNO_KEY,
    DeployStatus,
    MResConditionType,
    MResPhaseType,
)
from paas_wl.bk_app.cnative.specs.credentials import ImageCredentialsManager
from paas_wl.bk_app.cnative.specs.resource import MresConditionParser, deploy, get_mres_from_cluster
from paas_wl.infras.resources.utils.basic import get_client_by_app
from paas_wl.workloads.images.utils import make_image_pull_secret_name
from tests.paas_wl.bk_app.cnative.specs.utils import create_condition, create_res_with_conds
from tests.utils.mocks.engine import replace_cluster_service

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])
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

    def test_deploy_and_get_status_v1alpha1(self, bk_app, bk_stag_env, bk_stag_wl_app, mock_knamespace):
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

        with replace_cluster_service():
            ret = deploy(bk_stag_env, manifest)
        assert ret["spec"]["processes"][0]["name"] == "web"
        assert get_mres_from_cluster(bk_stag_env) is not None

        with get_client_by_app(bk_stag_wl_app) as client:
            assert (
                ImageCredentialsManager(client).get(bk_stag_wl_app, make_image_pull_secret_name(wl_app=bk_stag_wl_app))
                is not None
            )

        # 修改进程配置信息，再次部署到集群
        manifest["spec"]["processes"].append(
            {"name": "worker", "replicas": 1, "image": "busybox:latest", "cpu": "100m", "memory": "100Mi"}
        )
        with replace_cluster_service():
            ret = deploy(bk_stag_env, manifest)
        assert ret["spec"]["processes"][1]["name"] == "worker"

    def test_deploy_and_get_status_v1alpha2(self, bk_app, bk_stag_env, bk_stag_wl_app, mock_knamespace):
        manifest: Dict = {
            "apiVersion": "paas.bk.tencent.com/v1alpha2",
            "kind": "BkApp",
            "metadata": {"name": bk_app.code},
            "spec": {
                "build": {"image": "nginx:latest"},
                "processes": [{"name": "web", "replicas": 1, "resQuotaPlan": "default"}],
                "hooks": {"preRelease": {"command": ["/bin/echo"], "args": ["Hello"]}},
                "configuration": {"env": []},
            },
        }

        with replace_cluster_service():
            ret = deploy(bk_stag_env, manifest)

        assert ret["spec"]["processes"][0]["name"] == "web"
        assert get_mres_from_cluster(bk_stag_env) is not None

        # 修改进程配置信息，再次部署到集群
        manifest["spec"]["processes"].append({"name": "worker", "replicas": 1})
        with replace_cluster_service():
            ret = deploy(bk_stag_env, manifest)
        assert ret["spec"]["processes"][1]["name"] == "worker"
