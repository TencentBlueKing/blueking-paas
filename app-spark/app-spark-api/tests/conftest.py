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

"""pytest fixtures for app-spark-api tests."""

import pytest

from app_spark_api.core.projects.models import Project
from tests.helpers import create_user


@pytest.fixture()
def bk_user():
    """Generate a random user."""
    return create_user()


@pytest.fixture()
def project(bk_user):
    """Create a Project owned and created by the current BlueKing user."""
    return Project.objects.create(
        id="test-project",
        name="Test Project",
        creator=bk_user,
        owner=bk_user,
        tenant_id=bk_user.tenant_id,
    )
