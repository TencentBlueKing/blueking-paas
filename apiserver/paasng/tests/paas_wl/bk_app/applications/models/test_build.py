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
from paas_wl.bk_app.applications.models.build import Build, mark_as_latest_artifact

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


def test_mark_as_latest_artifact(bk_module, bk_stag_env, with_wl_apps):
    build_1 = Build.objects.create(module_id=bk_module.id, artifact_type=ArtifactType.IMAGE, image="nginx:latest")
    mark_as_latest_artifact(build_1)
    assert Build.objects.filter(module_id=bk_module.id, image="nginx:latest").count() == 1
    assert Build.objects.filter(module_id=bk_module.id, image="nginx:latest", artifact_deleted=False).count() == 1

    build_2 = Build.objects.create(module_id=bk_module.id, artifact_type=ArtifactType.IMAGE, image="nginx:latest")
    mark_as_latest_artifact(build_2)
    assert Build.objects.filter(module_id=bk_module.id, image="nginx:latest").count() == 2
    assert Build.objects.filter(module_id=bk_module.id, image="nginx:latest", artifact_deleted=False).count() == 1
