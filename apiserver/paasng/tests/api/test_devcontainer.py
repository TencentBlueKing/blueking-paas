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
from unittest import mock

import pytest

from paas_wl.bk_app.devcontainer.controller import DevContainerController
from paas_wl.bk_app.devcontainer.entities import ContainerDetail
from paas_wl.bk_app.devcontainer.exceptions import DevContainerAlreadyExists
from tests.utils.helpers import generate_random_string

pytestmark = pytest.mark.django_db


class TestDevContainerViewSet:
    def test_deploy(self, api_client, bk_app, bk_module):
        with mock.patch.object(DevContainerController, "deploy") as mocked_deploy:
            mocked_deploy.return_value = None
            response = api_client.post(
                f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/devcontainer/"
            )
            assert response.status_code == 201

    def test_deploy_when_already_exists(self, api_client, bk_app, bk_module):
        with mock.patch.object(DevContainerController, "deploy") as mocked_deploy:
            mocked_deploy.side_effect = DevContainerAlreadyExists
            response = api_client.post(
                f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/devcontainer/"
            )
            assert response.status_code == 409

    def test_delete(self, api_client, bk_app, bk_module):
        with mock.patch.object(DevContainerController, "delete") as mocked_delete:
            mocked_delete.return_value = None
            response = api_client.delete(
                f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/devcontainer/"
            )
            assert response.status_code == 204

    def test_get_container_detail(self, api_client, bk_app, bk_module):
        with mock.patch.object(DevContainerController, "get_container_detail") as mocked_get:
            token = generate_random_string(8)
            mocked_get.return_value = ContainerDetail(
                url="http://bkpaas.devcontainer.com", envs={"TOKEN": token}, status="Healthy"
            )
            response = api_client.get(f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/devcontainer/")
            assert response.status_code == 200
            assert response.data == {"url": "http://bkpaas.devcontainer.com", "token": token, "status": "Healthy"}
