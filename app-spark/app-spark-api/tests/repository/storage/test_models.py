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

import pytest

from app_spark_api.repository.storage.backends import SourceStorage
from app_spark_api.repository.storage.blob_stores import HostTmpPath
from app_spark_api.repository.storage.constants import StorageBackend
from app_spark_api.repository.storage.models import ProjectSourceStorage

pytestmark = pytest.mark.django_db


def test_project_source_storage_builds_backend(project, tmp_path):
    package_path = tmp_path / "source.tgz"
    source_storage = ProjectSourceStorage.objects.create(
        project=project,
        backend=StorageBackend.HOST_TMP_PATH,
        config={"path": str(package_path)},
    )

    backend = source_storage.get_backend()

    assert isinstance(backend, SourceStorage)
    assert isinstance(backend.blob_store, HostTmpPath)
    assert backend.blob_store.path == package_path
    assert project.source_storage == source_storage
