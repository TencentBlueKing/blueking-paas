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
from paas_wl.bk_app.applications.constants import ArtifactType
from paas_wl.bk_app.applications.models import Build


def mark_as_latest_artifact(build: "Build"):
    """mark the given build as latest artifact"""
    if build.artifact_type != ArtifactType.IMAGE:
        return
    # 旧的同名镜像会被覆盖, 则标记为已删除
    qs = Build.objects.filter(module_id=build.module_id, image=build.image).exclude(uuid=build.uuid)
    qs.update(artifact_deleted=True)
    return
