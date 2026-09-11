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

"""What local_process puts in a spawned Runtime's environment.

Two things are checked here: the public callback path is joined onto loopback, so
FORCE_SCRIPT_NAME comes off, and the Project's Git repository is described to the Runtime only
when there is one.
"""

from app_spark_api.agent.runtime.entities import GitRemote, LocalProcessConfig, StateCallback
from app_spark_api.agent.runtime.providers.local import ENV_PREFIX, LocalProcessProvider

PUBLIC_PATH = "/api-svc/api/internal/conversations/x/state/"
PATH_INFO = "/api/internal/conversations/x/state/"

REMOTE = GitRemote(
    clone_url="http://git.example/app-spark/p.git",
    branch="main",
    username="app-spark-bot",
    token="repo-scoped-token",
)


def _provider(tmp_path) -> LocalProcessProvider:
    return LocalProcessProvider(
        LocalProcessConfig(
            agent_project_dir="/srv/agent",
            workspace_root=str(tmp_path / "workspaces"),
            state_root=str(tmp_path / "state"),
            callback_base_url="http://127.0.0.1:8000",
        )
    )


def _build_env(tmp_path, *, state_callback=None, git_remote=None) -> dict[str, str]:
    """Build one Runtime's environment with everything but the varying part held fixed."""
    return _provider(tmp_path)._build_env(
        project_id="p",
        workspace_dir=tmp_path / "workspaces" / "p",
        state_dir=tmp_path / "state" / "c",
        runtime_token="runtime-token",
        state_callback=state_callback,
        git_remote=git_remote,
    )


def test_local_process_strips_force_script_name_from_the_callback(settings, tmp_path):
    settings.FORCE_SCRIPT_NAME = "/api-svc"

    env = _build_env(tmp_path, state_callback=StateCallback(path=PUBLIC_PATH, token="callback-token"))

    assert env[f"{ENV_PREFIX}CONTROL_PLANE_URL"] == f"http://127.0.0.1:8000{PATH_INFO}"


def test_local_process_keeps_an_unprefixed_callback_path(tmp_path):
    env = _build_env(tmp_path, state_callback=StateCallback(path=PATH_INFO, token="callback-token"))

    assert env[f"{ENV_PREFIX}CONTROL_PLANE_URL"] == f"http://127.0.0.1:8000{PATH_INFO}"


def test_a_git_remote_is_handed_to_the_runtime_that_will_write_to_it(tmp_path):
    env = _build_env(tmp_path, git_remote=REMOTE)

    assert env[f"{ENV_PREFIX}GIT_REMOTE_URL"] == REMOTE.clone_url
    assert env[f"{ENV_PREFIX}GIT_BRANCH"] == "main"
    assert env[f"{ENV_PREFIX}GIT_USERNAME"] == "app-spark-bot"
    assert env[f"{ENV_PREFIX}GIT_TOKEN"] == "repo-scoped-token"
    # So a commit can be traced back to the Project that produced it.
    assert env[f"{ENV_PREFIX}PROJECT_ID"] == "p"


def test_without_a_repository_the_runtime_is_told_nothing_about_git(tmp_path):
    # It then keeps its workspace on local disk and says so on `/health`, rather than behaving
    # as though the files were being saved somewhere.
    env = _build_env(tmp_path)

    assert f"{ENV_PREFIX}GIT_REMOTE_URL" not in env
    assert f"{ENV_PREFIX}GIT_TOKEN" not in env
