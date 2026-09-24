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

"""会话相关接口测试共用的构造函数。

刻意是普通函数，不是 `tests/api/conftest.py` 里的 fixture。同目录下 `test_git_repository.py` 和
`test_projects.py` 都不自带 `project`，吃的是根 conftest 那个（`id="test-project"`，租户取
`bk_user.tenant_id`）；把这里的版本放进 conftest 会顺着 fixture 覆盖规则悄悄改掉它们用的 Project
和租户。写成函数，哪个文件要用就自己包一层 fixture，谁也不会被动接管。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app_spark_api.core.projects.models import Project
from app_spark_api.core.tenant.user import get_tenant

if TYPE_CHECKING:
    from pathlib import Path

PROJECT_ID = "spark-demo"
CONVERSATIONS_URL = f"/api/projects/{PROJECT_ID}/conversations/"


def create_reachable_project(bk_user) -> Project:
    """Create a Project the logged-in caller can reach, scoped the way the API scopes it.

    租户取 `get_tenant()` 而不是 `bk_user.tenant_id`：根 conftest 的 `project` 用的是用户自己那个
    随机租户，而接口按 `get_tenant()` 过滤——没开多租户时它是 `default`，两者对不上就是 404。
    """
    return Project.objects.create(
        id=PROJECT_ID,
        name="Spark Demo",
        creator=bk_user,
        owner=bk_user,
        tenant_id=get_tenant(bk_user).id,
    )


def configure_local_provider(settings, tmp_path: Path) -> None:
    """Point the Agent Runtime provider at harmless paths.

    给那些根本不 spawn Runtime 的测试用：provider 只在构造时校验配置，不真的拉进程就不碰这些
    目录。真要起 agent 的测试（`test_conversations.py`）有自己那份，还得配回写地址和收尾。
    """
    settings.AGENT_RUNTIME_PROVIDER = "local_process"
    settings.AGENT_RUNTIME_PROVIDER_CONFIG = {
        "agent_project_dir": str(tmp_path / "agent"),
        "workspace_root": str(tmp_path / "workspaces"),
        "state_root": str(tmp_path / "agent-state"),
    }
    # 这些测试不关心模型从哪来。默认的 bkaidev 要先换票，会把它们卡在与本测试无关的配置上。
    settings.AGENT_MODEL_SOURCE = "direct"
    settings.AGENT_DIRECT_MODEL_CONFIG = {"model": "fake:chat"}
