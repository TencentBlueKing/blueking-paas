# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

from celery import shared_task

from paasng.platform.agent_sandbox.models import ImageBuildRecord
from paasng.platform.image_build.tasks import execute_image_build
from paasng.platform.sandbox_instance.models import SidecarImage


def _register_sidecar_image(build: ImageBuildRecord) -> None:
    """构建成功后，自动注册为可用 sidecar 镜像。"""
    SidecarImage.objects.get_or_create(
        app_code=build.app_code,
        image=build.output_image,
        tenant_id=build.tenant_id,
        defaults={
            "name": build.image_name,
            "tag": build.image_tag,
            "build_record": build,
        },
    )


@shared_task()
def run_sidecar_image_build(build_id: str):
    """异步执行 sidecar 镜像构建（纯 Kaniko 构建，不注入 daemon）。

    构建成功后自动创建 SidecarImage 记录。
    """
    execute_image_build(build_id, on_after_success=_register_sidecar_image)
