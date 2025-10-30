# -*- coding: utf-8 -*-
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

from blue_krill.storages.blobstore.base import SignatureType
from django.utils.timezone import now

from paas_wl.utils.blobstore import make_blob_store
from paasng.misc.tools.smart_app.build_phase import ALL_SMART_BUILD_PHASES
from paasng.misc.tools.smart_app.constants import SourceCodeOriginType
from paasng.misc.tools.smart_app.models import SmartBuildPhase, SmartBuildRecord, SmartBuildStep
from paasng.platform.engine.constants import JobStatus
from paasng.platform.sourcectl.package.utils import parse_url

from .tasks import execute_build, execute_build_error_callback


def create_smart_build_record(
    package_name: str,
    app_code: str,
    app_version: str,
    operator: str,
) -> SmartBuildRecord:
    """Initialize s-smart package build record

    :param package_name: The name of the source package file
    :param app_code: The code of the application
    :param app_version: The version from app_desc.yaml
    :param operator: The username who triggers this build
    :return: The created SmartBuildRecord instance
    """

    # TODO: 添加对源码仓库的支持
    source_origin = SourceCodeOriginType.PACKAGE

    record = SmartBuildRecord.objects.create(
        source_origin=source_origin,
        package_name=package_name,
        app_code=app_code,
        app_version=app_version,
        status=JobStatus.PENDING,
        start_time=now(),
        operator=operator,
    )
    record.refresh_from_db()

    # 初始化所有阶段和步骤
    for phase_config in ALL_SMART_BUILD_PHASES:
        phase = SmartBuildPhase.objects.create(
            smart_build=record,
            type=phase_config.type.value,
        )

        SmartBuildStep.objects.bulk_create(
            [
                SmartBuildStep(
                    phase=phase,
                    name=step.name,
                )
                for step in phase_config.steps
            ]
        )

    return record


class SmartBuildTaskRunner:
    """S-Mart builds a task executor"""

    def __init__(self, smart_build_id: str, source_url: str):
        self.smart_build_id = smart_build_id
        self.source_get_url = self._get_source_get_url(source_url)

        # 构建产物存储信息
        # TODO: 目前直接使用 prepared_packages 作为存储位置,后续可考虑单独创建一个存储桶
        self.artifact_bucket = parse_url(source_url).bucket
        self.artifact_key = f"smart_builder/artifact_{self.smart_build_id}.tar.gz"
        self.dest_put_url = self._generate_artifact_put_url()

    def start(self):
        """Start build task"""

        execute_build.apply_async(
            args=(
                self.smart_build_id,
                self.source_get_url,
                self.dest_put_url,
            ),
            link_error=execute_build_error_callback.s(),
        )

    def _get_source_get_url(self, source_url: str) -> str:
        """获取源码包下载 URL"""

        parsed = parse_url(source_url)
        return make_blob_store(parsed.bucket).generate_presigned_url(parsed.key, expires_in=3600)

    def _generate_artifact_put_url(self) -> str:
        """获取构建产物上传 URL"""

        # TODO: 目前直接使用 prepared_packages 作为存储位置,后续可考虑单独创建一个存储桶
        return make_blob_store(self.artifact_bucket).generate_presigned_url(
            self.artifact_key, expires_in=3600, signature_type=SignatureType.UPLOAD
        )
