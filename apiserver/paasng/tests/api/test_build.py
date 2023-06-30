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
import pytest

from paas_wl.utils.constants import BuildStatus
from tests.paas_wl.utils.build import create_build, create_build_proc

pytestmark = pytest.mark.django_db(databases=['default', 'workloads'])


class TestBuildProcessViewSet:
    def test_list_pending(self, api_client, bk_app, bk_module, bk_stag_env, with_wl_apps):
        bp = create_build_proc(bk_stag_env.wl_app)
        resp = api_client.get(
            path=f"/api/bkapps/applications/{bk_app.code}/modules/"
            f"{bk_module.name}/envs/{bk_stag_env.environment}/build/history/"
        )
        assert resp.status_code == 200

        data = resp.json()
        assert data["count"] == 1
        assert data["results"][0]["generation"] == bp.generation
        assert data["results"][0]["status"] == "pending"
        assert data["results"][0]["build_id"] is None

    def test_list_successful(self, api_client, bk_app, bk_module, bk_stag_env, with_wl_apps):
        bp = create_build_proc(bk_stag_env.wl_app)
        bp.update_status(BuildStatus.SUCCESSFUL)
        build = create_build(bk_stag_env.wl_app, image="nginx:latest", bp=bp)
        resp = api_client.get(
            path=f"/api/bkapps/applications/{bk_app.code}/modules/"
            f"{bk_module.name}/envs/{bk_stag_env.environment}/build/history/"
        )
        assert resp.status_code == 200

        data = resp.json()
        assert data["count"] == 1
        assert data["results"][0]["generation"] == bp.generation
        assert data["results"][0]["status"] == "successful"
        assert data["results"][0]["image_tag"] == "latest"
        assert data["results"][0]["build_id"] == str(build.uuid)
