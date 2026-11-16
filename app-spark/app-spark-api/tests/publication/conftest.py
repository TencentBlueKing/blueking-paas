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

"""Fixtures shared by publication tests."""

import pytest

from app_spark_api.infras.bk_paas import BkPaaSClient
from app_spark_api.publication.packaging import PackagedSource
from tests.publication.fake import FakeBkPaaSClient

CONSOLE_URL = "https://bkpaas.example.com"


@pytest.fixture()
def bkpaas(monkeypatch) -> FakeBkPaaSClient:
    """A developer center client that succeeds unless told otherwise.

    替换 from_settings，这样不接收客户端参数的调用（如校验应用名称）也打到它。
    """
    fake = FakeBkPaaSClient()
    monkeypatch.setattr(BkPaaSClient, "from_settings", lambda: fake)
    return fake


@pytest.fixture(autouse=True)
def packager(monkeypatch, settings) -> None:
    """Know versions v1 and v2 (the latest) and pack them instantly, and give the developer center a console address."""
    settings.BKPAAS_URL = CONSOLE_URL

    async def version_exists(project, version_id):
        return version_id in ("v1", "v2")

    async def latest_version(project):
        return "v2"

    async def package_version(project, version_id):
        return PackagedSource(f"{version_id}-abc1234", f"https://bkrepo.example.com/{version_id}")

    monkeypatch.setattr("app_spark_api.publication.packaging.aversion_exists", version_exists)
    monkeypatch.setattr("app_spark_api.publication.packaging.alatest_version", latest_version)
    monkeypatch.setattr("app_spark_api.publication.packaging.apackage_version", package_version)


@pytest.fixture(autouse=True)
def queued(monkeypatch) -> list[tuple]:
    """Record the messages that would be queued on RabbitMQ instead of sending them."""
    messages: list[tuple] = []
    monkeypatch.setattr(
        "app_spark_api.publication.tasks.schedule_deployment_prepare",
        lambda *args: messages.append(("prepare", *args)),
    )
    monkeypatch.setattr(
        "app_spark_api.publication.tasks.schedule_deployment_poll", lambda *args: messages.append(("poll", *args))
    )
    return messages
