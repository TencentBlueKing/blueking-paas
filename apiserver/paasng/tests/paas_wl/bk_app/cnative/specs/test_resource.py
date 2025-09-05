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

import logging
from typing import Dict
from unittest import mock

import pytest
from kubernetes.client.exceptions import ApiException

from paas_wl.bk_app.cnative.specs.constants import DeployStatus, MResConditionType, MResPhaseType
from paas_wl.bk_app.cnative.specs.resource import (
    MresConditionParser,
    create_or_update_bkapp_with_retries,
    deploy,
    get_mres_from_cluster,
    list_mres_by_env,
)
from paas_wl.infras.resources.utils.basic import get_client_by_app
from tests.paas_wl.bk_app.cnative.specs.utils import create_condition, create_res, with_conds

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])
logger = logging.getLogger(__name__)


class TestMresConditionDetector:
    @pytest.mark.parametrize(
        ("mres", "expected_status"),
        [
            (create_res(with_conds([])), DeployStatus.PENDING),
            (
                create_res(with_conds([create_condition(MResConditionType.APP_AVAILABLE)])),
                DeployStatus.PROGRESSING,
            ),
            (
                create_res(
                    with_conds([create_condition(MResConditionType.APP_AVAILABLE, "True")], MResPhaseType.AppRunning)
                ),
                DeployStatus.READY,
            ),
            (
                create_res(
                    with_conds(
                        [create_condition(MResConditionType.ADDONS_PROVISIONED, "False")], MResPhaseType.AppFailed
                    )
                ),
                DeployStatus.ERROR,
            ),
            (
                create_res(
                    with_conds(
                        [
                            create_condition(MResConditionType.ADDONS_PROVISIONED, "False"),
                            create_condition(MResConditionType.APP_AVAILABLE, "True"),
                        ],
                        MResPhaseType.AppFailed,
                    )
                ),
                DeployStatus.ERROR,
            ),
        ],
    )
    def test_detect(self, mres, expected_status):
        s = MresConditionParser(mres).detect_state()
        assert s.status == expected_status


@pytest.mark.skip_when_no_crds()
class TestBkAppClusterOperator:
    """测试在集群中操作 bkapp 资源"""

    @pytest.mark.usefixtures("_with_stag_ns")
    def test_deploy_and_get_status_v1alpha2(self, bk_app, bk_stag_env, bk_stag_wl_app):
        manifest: Dict = {
            "apiVersion": "paas.bk.tencent.com/v1alpha2",
            "kind": "BkApp",
            "metadata": {
                "name": bk_app.code,
                "annotations": {
                    "bkapp.paas.bk.tencent.com/code": bk_app.code,
                    "bkapp.paas.bk.tencent.com/module-name": bk_stag_env.module.name,
                },
            },
            "spec": {
                "build": {"image": "nginx:latest"},
                "processes": [{"name": "web", "replicas": 1, "resQuotaPlan": "default"}],
                "hooks": {"preRelease": {"command": ["/bin/echo"], "args": ["Hello"]}},
                "configuration": {"env": []},
            },
        }

        ret = deploy(bk_stag_env, manifest)

        assert ret["spec"]["processes"][0]["name"] == "web"
        assert get_mres_from_cluster(bk_stag_env) is not None

        # 修改进程配置信息，再次部署到集群
        manifest["spec"]["processes"].append({"name": "worker", "replicas": 1})
        ret = deploy(bk_stag_env, manifest)
        assert ret["spec"]["processes"][1]["name"] == "worker"

    @pytest.mark.usefixtures("_with_stag_ns")
    def test_create_or_update_bkapp_with_retries(self, bk_app, bk_stag_env, bk_stag_wl_app):
        """测试下发 bkapp 资源时的重试逻辑"""
        counter = 0

        def create_or_update_side_effect(*args, **kwargs):
            # 使用 nonlocal 关键字来访问外部的计数器变量
            nonlocal counter
            if counter == 0:
                # 第一次调用，抛出 ApiException
                counter += 1
                e = ApiException(status=409)
                e.body = '{"reason": "Conflict"}'
                raise e
            else:
                return "success", False

        manifest = mock.MagicMock()
        metadata = mock.MagicMock()
        manifest.__getitem__.side_effect = {
            "apiVersion": "paas.bk.tencent.com/v1alpha2",
            "kind": "BkApp",
            "metadata": metadata,
        }.get
        with mock.patch(
            "paas_wl.infras.resources.base.crd.BkApp.create_or_update", side_effect=create_or_update_side_effect
        ) as mocked_create_or_update:
            client = get_client_by_app(bk_stag_wl_app)
            create_or_update_bkapp_with_retries(client, bk_stag_env, manifest)

        assert mocked_create_or_update.call_count == 2
        assert metadata.pop.call_count == 1


@pytest.mark.skip_when_no_crds()
class Test__list_mres_by_env:
    @pytest.mark.usefixtures("_with_stag_ns")
    def test_list(self, bk_app, bk_stag_env):
        manifest = {
            "apiVersion": "paas.bk.tencent.com/v1alpha2",
            "kind": "BkApp",
            "metadata": {
                "name": bk_app.code,
                "annotations": {
                    "bkapp.paas.bk.tencent.com/code": bk_app.code,
                    "bkapp.paas.bk.tencent.com/module-name": bk_stag_env.module.name,
                },
            },
            "spec": {
                "build": {"image": "nginx:latest"},
                "processes": [{"name": "web", "replicas": 1, "resQuotaPlan": "default"}],
                "hooks": {"preRelease": {"command": ["/bin/echo"], "args": ["Hello"]}},
                "configuration": {},
            },
        }

        deploy(bk_stag_env, manifest)

        res = list_mres_by_env(bk_app, bk_stag_env.environment)[0]
        assert res.metadata.name == bk_app.code
        assert res.spec.processes[0].name == "web"
        assert res.spec.processes[0].resQuotaPlan == "default"
