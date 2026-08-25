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

from django.db import models

from app_spark_api.repository.storage.backends import SourceStorage, make_storage_backend
from app_spark_api.utils.models import TimestampedModel


class ProjectSourceStorage(TimestampedModel):
    """Persist the storage backend currently used by a Project's source code."""

    project = models.OneToOneField(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="source_storage",
    )
    # 当前支持 host_tmp_path 与 bk_repo，实际取值校验由 make_storage_backend 负责。
    backend = models.CharField(max_length=32, help_text="源码存储引擎，例如 host_tmp_path 或 bk_repo")
    config = models.JSONField(
        default=dict,
        help_text=(
            '存储引擎配置，例如 HostTmpPath 使用 {"path": "/tmp/project-source.tgz"}，'
            'BkRepo 使用 {"bucket": "project-source", "key": "projects/demo/source.tgz"}'
        ),
    )

    def get_backend(self) -> SourceStorage:
        """Build the configured source storage backend."""
        return make_storage_backend(self.backend, self.config)
