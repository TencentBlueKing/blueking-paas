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

import random

import pytest
from django.utils.crypto import get_random_string

from paas_wl.bk_app.cnative.specs.models import AppModelResource, create_app_resource

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture()
def base_manifest(bk_app):
    """A very basic manifest that can pass the validation."""
    return {
        "kind": "BkApp",
        "apiVersion": "paas.bk.tencent.com/v1alpha2",
        "metadata": {"name": bk_app.code},
        "spec": {
            "build": {"image": "nginx:latest"},
            "processes": [{"name": "web", "replicas": 1, "resQuotaPlan": "default"}],
        },
    }


@pytest.fixture()
def random_resource_name():
    """A random name used as kubernetes resource name to avoid conflict
    can also be used for application name
    """
    return "bkapp-" + get_random_string(length=12).lower() + "-" + random.choice(["stag", "prod"])


@pytest.fixture()
def init_model_resource(bk_app, bk_module, random_resource_name):
    """Initialize the app model resource"""
    resource = create_app_resource(
        # Use Application code as default resource name
        name=random_resource_name,
        image="nginx:latest",
        command=None,
        args=None,
        target_port=None,
    )
    return AppModelResource.objects.create_from_resource(bk_app, bk_module.id, resource)


class TestManifestViewSet:
    def test_import(self, api_client, bk_app, bk_module, bk_stag_env, init_model_resource, base_manifest):
        url = f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/bkapp_model/manifests/current/"

        response = api_client.put(url, {"manifest": base_manifest})
        assert response.data[0]["metadata"]["name"] == bk_app.code
        assert response.status_code == 200
