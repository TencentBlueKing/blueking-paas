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

"""Loading the configured repo-server (Git persistence host)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.core.signals import setting_changed
from django.dispatch import receiver

from app_spark_api.infras.forgejo.client import ForgejoClient
from app_spark_api.repository.git.entities import RepoServerConfig, structure_repo_server_config

if TYPE_CHECKING:
    import httpx2

_config: RepoServerConfig | None = None


def get_repo_server_config() -> RepoServerConfig:
    """Return the process-wide repo-server configuration."""
    global _config
    if _config is None:
        _config = structure_repo_server_config(getattr(settings, "REPO_SERVER", None))
    return _config


def make_forgejo_client(
    config: RepoServerConfig | None = None,
    *,
    transport: httpx2.BaseTransport | None = None,
) -> ForgejoClient:
    """Build a Forgejo client from ``REPO_SERVER``.

    :param config: Defaults to the process-wide settings.
    :param transport: Optional httpx transport for tests.
    """
    resolved = config or get_repo_server_config()
    return ForgejoClient(resolved.forgejo_client_config(), transport=transport)


@receiver(setting_changed)
def _reset_config(*, setting: str, **kwargs: object) -> None:
    if setting == "REPO_SERVER":
        global _config
        _config = None
