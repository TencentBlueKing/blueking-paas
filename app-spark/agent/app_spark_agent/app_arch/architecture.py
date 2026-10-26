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

"""Compose the application-architecture operations exposed to tools and the supervisor.

AppArchitecture is the main entry point for consumers of app_arch. The files synchronized by
sync are:

- app_desc.yaml: the Developer Center process and service declaration, rendered by app_desc;
- .python-version: the Python runtime selector, rendered by python.

init_project and sync are deliberately separate:

- init_project is one-time project creation. It takes a project name, creates pyproject.toml
  and uv.lock from the Python template only when pyproject.toml is absent, and then runs sync.
  An existing pyproject.toml returns unchanged immediately: initialization never replaces the
  project's dependency baseline, and repairing generated files remains sync's job;
- sync is repeatable maintenance. It takes no project name, never creates or rewrites
  pyproject.toml or uv.lock, and can run whenever generated files are missing or stale,
  including immediately before every application launch.

In short, init_project establishes the project once; sync keeps its generated architecture
files correct over time.
"""

from pathlib import Path

from app_spark_agent.app_arch.app_desc import APP_DESC_FILENAME, sync_app_desc
from app_spark_agent.app_arch.files import (
    FileSyncResult,
    FileSyncStatus,
    merge_sync_results,
)
from app_spark_agent.app_arch.python import (
    PYTHON_VERSION_FILENAME,
    sync_python_project,
    sync_python_version,
)

SYNC_FILENAMES = (APP_DESC_FILENAME, PYTHON_VERSION_FILENAME)


class AppArchitecture:
    """Main entry point for initializing and synchronizing an Agent-built application."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace

    def init_project(self, raw_name: str, port: int) -> FileSyncResult:
        """Create the Python project once, then synchronize its generated files."""
        project = sync_python_project(self.workspace, raw_name)
        if project.status is not FileSyncStatus.SYNCED:
            return project

        return merge_sync_results(project, self.sync(port))

    def sync(self, port: int) -> FileSyncResult:
        """Create or repair the generated architecture files without touching the project baseline."""
        return merge_sync_results(
            sync_app_desc(self.workspace, port),
            sync_python_version(self.workspace),
        )
