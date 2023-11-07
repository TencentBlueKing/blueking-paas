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
import json

import pytest
from django.utils.crypto import get_random_string

from paas_wl.bk_app.deploy.app_res.client import K8sScheduler
from paas_wl.infras.resources.kube_res.exceptions import AppEntityNotFound
from paas_wl.utils.text import b64decode, b64encode
from paas_wl.workloads.images import constants
from paas_wl.workloads.images.kres_entities import credentials_kmodel
from paas_wl.workloads.images.models import AppImageCredential
from paas_wl.workloads.images.utils import make_image_pull_secret_name

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.mark.auto_create_ns
class TestImageCredentialsHandler:
    @pytest.fixture
    def kube_res_name(self, wl_app):
        return make_image_pull_secret_name(wl_app=wl_app)

    @pytest.fixture(autouse=True)
    def clear_builtin_auth(self, settings):
        settings.APP_DOCKER_REGISTRY_HOST = ""

    def test_create_empty(self, wl_app, kube_res_name, scheduler_client: K8sScheduler):
        scheduler_client.ensure_image_credentials_secret(wl_app)
        obj = credentials_kmodel.get(wl_app, name=kube_res_name)
        assert len(obj.credentials) == 0
        assert obj.name == kube_res_name
        assert obj._kube_data.data[constants.KUBE_DATA_KEY] == b64encode('{"auths": {}}')

    def test_create(self, wl_app, kube_res_name, scheduler_client: K8sScheduler):
        registry = get_random_string()
        username = get_random_string()
        password = get_random_string()

        AppImageCredential.objects.create(app=wl_app, registry=registry, username=username, password=password)

        scheduler_client.ensure_image_credentials_secret(wl_app)
        obj = credentials_kmodel.get(wl_app, name=kube_res_name)
        assert len(obj.credentials) == 1
        assert obj.name == kube_res_name
        assert json.loads(b64decode(obj._kube_data.data[constants.KUBE_DATA_KEY])) == {
            "auths": {
                registry: {"username": username, "password": password, "auth": b64encode(f"{username}:{password}")}
            }
        }

    def test_update(self, wl_app, kube_res_name, scheduler_client: K8sScheduler):
        scheduler_client.ensure_image_credentials_secret(wl_app)
        obj = credentials_kmodel.get(wl_app, name=kube_res_name)
        assert len(obj.credentials) == 0

        AppImageCredential.objects.create(app=wl_app, registry="foo", username="bar", password="baz")
        scheduler_client.ensure_image_credentials_secret(wl_app)
        obj = credentials_kmodel.get(wl_app, name=kube_res_name)
        assert len(obj.credentials) == 1

    def test_not_found(self, wl_app, kube_res_name):
        with pytest.raises(AppEntityNotFound):
            credentials_kmodel.get(wl_app, name=kube_res_name)
