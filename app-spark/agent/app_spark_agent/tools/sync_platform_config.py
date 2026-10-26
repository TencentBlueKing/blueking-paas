# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

"""Model tool for repairing platform-owned project configuration."""

from collections.abc import Callable
from pathlib import Path

from app_spark_agent import settings
from app_spark_agent.app_arch.architecture import AppArchitecture
from app_spark_agent.app_arch.files import FileSyncResult


def build_sync_platform_config_tool(workspace: Path, *, port: int | None = None) -> Callable[[], FileSyncResult]:
    """Return the platform configuration repair tool bound to workspace."""
    architecture = AppArchitecture(workspace)
    target_port = settings.APP_PORT if port is None else port

    def sync_platform_config() -> FileSyncResult:
        """Create or repair the platform-owned files required to deploy this application.

        Takes no arguments. It synchronizes `app_desc.yaml` with the platform's launch command
        and port, and pins `.python-version` to the supported Python runtime. Do not edit either
        generated file by hand.
        """
        return architecture.sync(target_port)

    return sync_platform_config
