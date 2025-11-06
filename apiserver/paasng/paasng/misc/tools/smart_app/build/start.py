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
from django.utils import timezone

from paas_wl.utils.blobstore import make_blob_store
from paasng.misc.tools.smart_app.build.flow import SmartBuildStateMgr
from paasng.misc.tools.smart_app.constants import SourceCodeOriginType
from paasng.misc.tools.smart_app.models import SmartBuildRecord
from paasng.misc.tools.smart_app.output import make_channel_stream
from paasng.platform.engine.constants import JobStatus
from paasng.platform.sourcectl.package.utils import parse_url

from .tasks import execute_build, execute_build_error_callback


def create_smart_build_record(
    package_name: str,
    app_code: str,
    app_version: str,
    sha256_signature: str,
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
        sha256_signature=sha256_signature,
        start_time=timezone.now(),
        operator=operator,
    )

    return record


class SmartBuildContext:
    """S-Mart Build Context"""

    def __init__(
        self,
        smart_build: SmartBuildRecord,
        source_url: str,
        artifact_key: str,
    ):
        self.smart_build = smart_build
        self.source_url = source_url
        self.artifact_key = artifact_key

        # TODO: 目前直接使用 prepared_packages 作为存储位置, 后续可考虑单独创建一个存储桶
        self.artifact_bucket = parse_url(source_url).bucket

    def get_source_get_url(self) -> str:
        """获取源码包下载 URL"""
        parsed = parse_url(self.source_url)
        return make_blob_store(parsed.bucket).generate_presigned_url(parsed.key, expires_in=600)

    def get_artifact_put_url(self) -> str:
        """获取构建产物上传 URL"""
        return make_blob_store(self.artifact_bucket).generate_presigned_url(
            self.artifact_key, expires_in=600, signature_type=SignatureType.UPLOAD
        )

    def get_artifact_url(self) -> str:
        """存储于数据库中的 URL, 用于后续创建临时下载链接"""
        return f"blobstore://{self.artifact_bucket}/{self.artifact_key}"

    @staticmethod
    def generate_artifact_key(app_code: str, app_version: str, sha256_signature: str) -> str:
        """Generate standardized build artifact key"""
        return f"{app_code}-{app_version}_paas3_{sha256_signature[:7]}.tar.gz"


class SmartBuildTaskRunner:
    """S-Mart builds a task executor

    :param smart_build_id: The ID of the smart build record
    :param source_url: The source package URL
    :param app_code: The code of the application
    :param app_version: The version of the application
    :param sha256_signature: The sha256 signature of the source package
    """

    def __init__(
        self,
        smart_build_id: str,
        source_url: str,
        app_code: str,
        app_version: str,
        sha256_signature: str,
    ):
        self.smart_build = SmartBuildRecord.objects.get(uuid=smart_build_id)
        artifact_key = SmartBuildContext.generate_artifact_key(app_code, app_version, sha256_signature)
        self._context = SmartBuildContext(self.smart_build, source_url, artifact_key)

    def start(self):
        """Start build task"""

        self.prepare()

        # NOTE: artifact_key 是格式化命名的, 其中包含源码包的 sha256 签名前 7 位,
        # 可能存在不同源码包内容但 sha256 签名前 7 位相同的情况, 导致制品命中误判
        if self._artifact_exists(self._context.artifact_key):
            self._skip_build_with_cached_artifact()
            return

        execute_build.apply_async(
            args=(
                self.smart_build.uuid,
                self._context.get_source_get_url(),
                self._context.get_artifact_put_url(),
            ),
            link_error=execute_build_error_callback.s(),
        )

    def prepare(self):
        """Prepare the build environment and save the build artifact information."""
        smart_build = self.smart_build
        smart_build.artifact_url = self._context.get_artifact_url()
        smart_build.save(update_fields=["artifact_url"])

    def _artifact_exists(self, artifact_key: str):
        """检查对象存储中制品是否存在"""
        blob_store = make_blob_store(self._context.artifact_bucket)
        try:
            return blob_store.get_file_metadata(artifact_key) is not None
        except Exception:
            return False

    def _skip_build_with_cached_artifact(self):
        """使用缓存制品直接标记构建成功，跳过实际构建过程"""
        stream = make_channel_stream(self.smart_build)
        state_mgr = SmartBuildStateMgr.from_smart_build_id(self.smart_build.uuid, stream)

        state_mgr.start()
        stream.write_message("Build artifact cache hit, skip building process.")
        state_mgr.finish(JobStatus.SUCCESSFUL)

        stream.close()
        state_mgr.coordinator.release_lock(self.smart_build)
