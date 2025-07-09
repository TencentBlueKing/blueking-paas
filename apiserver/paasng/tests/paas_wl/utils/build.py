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

from typing import Optional

from django.utils.crypto import get_random_string

from paas_wl.bk_app.applications.constants import ArtifactType
from paas_wl.bk_app.applications.managers import mark_as_latest_artifact
from paas_wl.bk_app.applications.models.build import Build, BuildProcess
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.sourcectl.models import VersionInfo


def create_build_proc(
    env: ModuleEnvironment, source_tar_path=None, revision=None, branch=None, image=None, buildpacks=None
) -> BuildProcess:
    """Create a BuildProcess object"""
    source_tar_path = source_tar_path or get_random_string(10)
    revision = revision or get_random_string(10)
    branch = branch or get_random_string(10)

    build_process = BuildProcess.objects.new(
        env=env,
        owner=env.application.owner,
        builder_image=image,
        source_tar_path=source_tar_path,
        version_info=VersionInfo(revision=revision, version_name=branch, version_type="branch"),
        invoke_message="",
        buildpacks_info=buildpacks or [],
    )
    return build_process


def create_build(
    env: ModuleEnvironment,
    image: str = "",
    bp: Optional[BuildProcess] = None,
    artifact_type: ArtifactType = ArtifactType.IMAGE,
):
    branch = bp.branch if bp is not None else "master"
    revision = bp.revision if bp is not None else "1"
    wl_app = env.wl_app
    build_params = {
        "owner": wl_app.owner,
        "application_id": env.application_id,
        "module_id": env.module_id,
        "app": wl_app,
        "image": image or "nginx:latest",
        "source_type": "foo",
        "branch": branch,
        "revision": revision,
        "artifact_type": artifact_type,
    }
    wl_build = Build.objects.create(tenant_id=wl_app.tenant_id, **build_params)
    mark_as_latest_artifact(wl_build)
    if bp:
        bp.build = wl_build
        bp.save()
    return wl_build
