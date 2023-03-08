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
from django.utils.crypto import get_random_string

from paas_wl.platform.applications.models import BuildProcess, OutputStream, WlApp


def create_build_proc(app: WlApp, source_tar_path=None, revision=None, branch=None, image=None, buildpacks=None):
    """Create a BuildProcess object

    :param app: The WlApp object
    """
    source_tar_path = source_tar_path or get_random_string(10)
    revision = revision or get_random_string(10)
    branch = branch or get_random_string(10)

    build_process = BuildProcess.objects.create(
        owner=app.owner,
        app=app,
        source_tar_path=source_tar_path,
        revision=revision,
        branch=branch,
        output_stream=OutputStream.objects.create(),
        # 允许 none 参数
        image=image,
        buildpacks=buildpacks,
    )
    return build_process
