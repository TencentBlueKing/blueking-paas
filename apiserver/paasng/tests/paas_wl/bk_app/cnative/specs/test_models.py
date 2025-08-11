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

import pytest

from paas_wl.bk_app.cnative.specs.models import (
    AppModelDeploy,
    AppModelResource,
    create_app_resource,
    generate_bkapp_name,
)
from tests.paas_wl.bk_app.cnative.specs.utils import create_cnative_deploy

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestCreateAppResource:
    @pytest.fixture()
    def bkapp_manifest(self):
        return {
            "apiVersion": "paas.bk.tencent.com/v1alpha2",
            "kind": "BkApp",
            "metadata": {"name": "foo-app", "annotations": {}, "generation": 0},
            "spec": {
                "build": {
                    "args": None,
                    "buildTarget": None,
                    "dockerfile": None,
                    "image": "nginx:latest",
                    "imageCredentialsName": None,
                    "imagePullPolicy": "IfNotPresent",
                },
                "processes": [
                    {
                        "name": "web",
                        "replicas": 1,
                        "command": [],
                        "components": None,
                        "args": [],
                        "targetPort": None,
                        "services": None,
                        "resQuotaPlan": None,
                        "autoscaling": None,
                        "probes": None,
                    }
                ],
                "hooks": None,
                "addons": [],
                "mounts": None,
                "envOverlay": None,
                "domainResolution": None,
                "svcDiscovery": None,
                "configuration": {"env": []},
                "observability": None,
            },
            "status": {
                "conditions": [],
                "lastUpdate": None,
                "phase": "Pending",
                "observedGeneration": 0,
                "deployId": "",
            },
        }

    def test_v1alpha2(self, bkapp_manifest):
        obj = create_app_resource("foo-app", "nginx:latest")
        assert obj.dict() == bkapp_manifest


@pytest.fixture()
def spec_example():
    """An example spec"""
    return {
        "processes": [
            {
                "name": "web",
                "image": "nginx:latest",
                "replicas": 1,
                "command": [],
                "args": [],
                "targetPort": None,
            }
        ],
        "configuration": {"env": []},
    }


@pytest.fixture()
def resource_name(bk_app):
    """Make a name which follows the constraints of metadata.name"""
    return "res-" + bk_app.code


@pytest.fixture()
def init_model_resource(bk_app, bk_module, resource_name):
    """Initialize the app model resource"""
    resource = create_app_resource(
        # Use Application code as default resource name
        name=resource_name,
        image="nginx:latest",
        command=None,
        args=None,
        target_port=None,
    )
    return AppModelResource.objects.create_from_resource(bk_app, bk_module.id, resource)


class TestAppModelDeploy:
    def test_filter_by_env(self, bk_stag_env, bk_user):
        assert AppModelDeploy.objects.filter_by_env(bk_stag_env).count() == 0
        create_cnative_deploy(bk_stag_env, bk_user)
        assert AppModelDeploy.objects.filter_by_env(bk_stag_env).count() == 1

    def test_any_successful(self, bk_stag_env, bk_user):
        assert AppModelDeploy.objects.any_successful(bk_stag_env) is False
        # Initialize the app model resource and create a successful deployment
        create_cnative_deploy(bk_stag_env, bk_user)
        assert AppModelDeploy.objects.any_successful(bk_stag_env) is True


def test_bkapp_name_with_default_module(bk_app, bk_stag_env):
    assert generate_bkapp_name(bk_stag_env) == bk_app.code
