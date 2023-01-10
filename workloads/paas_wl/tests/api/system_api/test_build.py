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

from paas_wl.platform.applications.models import Release
from paas_wl.release_controller.builder import tasks

pytestmark = pytest.mark.django_db


class TestBuildProcessViewSet:
    def test_create_build_process(self, create_build_process):
        response, _ = create_build_process()
        assert response.status_code == 201
        assert response.json()["status"] == "pending"

    @pytest.mark.auto_create_ns
    def test_retrieve_result(self, engine_app, create_build_process, api_client, mock_bp_executor):
        create_response, start_build_process_args = create_build_process()
        build = create_response.json()["uuid"]
        retrieve_result_url = f'/regions/{engine_app.region}/apps/{engine_app.name}/build_processes/{build}/result'
        response = api_client.get(retrieve_result_url)

        assert response.status_code == 200
        assert response.json()["status"] == "pending"

        tasks.start_build_process(*start_build_process_args[0], **start_build_process_args[1])
        response = api_client.get(retrieve_result_url)
        assert response.status_code == 200
        assert response.json()["status"] == 'successful'

    @pytest.mark.auto_create_ns
    def test_list_builds(self, engine_app, api_client, create_build_process, mock_bp_executor):
        url = f'/regions/{engine_app.region}/apps/{engine_app.name}/builds/'
        response = api_client.get(url)

        assert response.status_code == 200
        assert response.json() == {"count": 0, "next": None, "previous": None, "results": []}

        _, start_build_process_args = create_build_process()
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.json()["count"] == 0

        tasks.start_build_process(*start_build_process_args[0], **start_build_process_args[1])
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.json()["count"] == 1


class TestReleaseViewSet:
    @pytest.mark.mock_get_structured_app
    @pytest.mark.auto_create_ns
    def testcase(self, build, bk_stag_engine_app, api_client, release_url, create_release):
        response = create_release()
        assert response.status_code == 201
        assert response.json()["failed"] is False

        data = {"release_id": str(Release.objects.get_latest(bk_stag_engine_app).uuid)}
        with mock.patch('rest_framework.request.Request.data', data):
            response = api_client.get(release_url)
        assert response.status_code == 200
        assert response.json()["failed"] is False
