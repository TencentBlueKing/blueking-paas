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

from paas_wl.bk_app.applications.constants import ArtifactType
from paas_wl.utils.constants import BuildStatus
from tests.paas_wl.utils.build import create_build, create_build_proc

pytestmark = [
    pytest.mark.django_db(databases=["default", "workloads"]),
    pytest.mark.usefixtures("_with_wl_apps"),
]


class TestImageArtifactViewSet:
    def test_list(self, api_client, bk_app, bk_module, bk_stag_env):
        bp = create_build_proc(bk_stag_env)
        bp.update_status(BuildStatus.SUCCESSFUL)
        build = create_build(bk_stag_env, image="nginx:latest", bp=bp, artifact_type=ArtifactType.IMAGE)
        build.artifact_detail = {
            "size": 56716959,
            "digest": "sha256:63aa22a3a677b20b74f4c977a418576934026d8562c04f6a635f0e71e0686b6d",
            "invoke_message": "",
        }
        build.save()

        resp = api_client.get(
            path=f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/build/artifact/image/"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["results"][0]["id"] == str(build.uuid)
        assert data["results"][0]["size"] == build.artifact_detail["size"]
        assert data["results"][0]["digest"] == build.artifact_detail["digest"]

    # 测试相同镜像会覆盖旧的镜像信息
    def test_list_duplicated(self, api_client, bk_app, bk_module, bk_stag_env):
        bp = create_build_proc(bk_stag_env)
        bp.update_status(BuildStatus.SUCCESSFUL)
        build_1 = create_build(bk_stag_env, image="nginx:latest", bp=bp, artifact_type=ArtifactType.IMAGE)
        build_1.artifact_detail = {
            "size": 56716959,
            "digest": "sha256:63aa22a3a677b20b74f4c977a418576934026d8562c04f6a635f0e71e0686b6d",
            "invoke_message": "",
        }
        build_1.save()

        build_2 = create_build(bk_stag_env, image="nginx:latest", bp=bp, artifact_type=ArtifactType.IMAGE)
        build_2.artifact_detail = {
            "size": 53430460,
            "digest": "sha256:a5a1e8e5148de5ebc9697b64e4edb2296b5aac1f05def82efdc00ccb7b457171",
            "invoke_message": "",
        }
        build_2.save()

        resp = api_client.get(
            path=f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/build/artifact/image/"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["results"][0]["id"] == str(build_2.uuid)
        assert data["results"][0]["size"] == build_2.artifact_detail["size"]
        assert data["results"][0]["digest"] == build_2.artifact_detail["digest"]

    def test_retrieve_image_detail(self, api_client, bk_app, bk_module, bk_stag_env):
        bp = create_build_proc(bk_stag_env)
        bp.update_status(BuildStatus.SUCCESSFUL)
        build_1 = create_build(bk_stag_env, image="nginx:latest", bp=bp, artifact_type=ArtifactType.IMAGE)
        build_1.artifact_detail = {
            "size": 56716959,
            "digest": "sha256:63aa22a3a677b20b74f4c977a418576934026d8562c04f6a635f0e71e0686b6d",
            "invoke_message": "",
        }
        build_1.save()

        build_2 = create_build(bk_stag_env, image="nginx:latest", bp=bp, artifact_type=ArtifactType.IMAGE)
        build_2.artifact_detail = {
            "size": 53430460,
            "digest": "sha256:a5a1e8e5148de5ebc9697b64e4edb2296b5aac1f05def82efdc00ccb7b457171",
            "invoke_message": "",
        }
        build_2.save()

        resp = api_client.get(
            path=f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/build/artifact/image/{build_2.uuid}"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["image_info"]["digest"] == build_2.artifact_detail["digest"]
        assert len(data["build_records"]) == 2
        assert data["build_records"][0]["id"] == str(build_2.uuid)
        assert data["build_records"][1]["id"] == str(build_1.uuid)


class TestBuildProcessViewSet:
    def test_list_pending(self, api_client, bk_app, bk_module, bk_stag_env):
        bp = create_build_proc(bk_stag_env)
        resp = api_client.get(path=f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/build_process/")
        assert resp.status_code == 200

        data = resp.json()
        assert data["count"] == 1
        assert data["results"][0]["generation"] == bp.generation
        assert data["results"][0]["status"] == "pending"
        assert data["results"][0]["build_id"] is None

    def test_list_successful(self, api_client, bk_app, bk_module, bk_stag_env):
        bp = create_build_proc(bk_stag_env)
        bp.update_status(BuildStatus.SUCCESSFUL)
        build = create_build(bk_stag_env, image="nginx:latest", bp=bp, artifact_type=ArtifactType.IMAGE)
        resp = api_client.get(path=f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/build_process/")
        assert resp.status_code == 200

        data = resp.json()
        assert data["count"] == 1
        assert data["results"][0]["generation"] == bp.generation
        assert data["results"][0]["status"] == "successful"
        assert data["results"][0]["image_tag"] == "latest"
        assert data["results"][0]["build_id"] == str(build.uuid)
