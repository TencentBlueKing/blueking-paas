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

from __future__ import annotations

import os

import pytest

from app_spark_api.core.projects.models import Project
from tests.helpers import create_user
from tests.infras.forgejo.fake import FakeForgejo, repo_server_config

if os.environ.get("APP_SPARK_FORGEJO_LIVE") != "1":
    collect_ignore = ["api/live_forgejo"]


@pytest.fixture(autouse=True)
def fake_forgejo(settings, monkeypatch, request):
    """Git persistence is always on. Unit tests talk to an in-memory Forgejo.

    Live Forgejo jobs (``@pytest.mark.forgejo``) keep the real client.
    """
    fake = FakeForgejo()
    if request.node.get_closest_marker("forgejo"):
        yield fake
        return
    settings.REPO_SERVER = repo_server_config()
    monkeypatch.setattr("app_spark_api.repository.git.services.make_forgejo_client", fake.client)
    yield fake


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
