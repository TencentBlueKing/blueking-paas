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

"""What local_process puts in a spawned Runtime's environment, and where it proxies previews to.

Three things are checked here: the public callback path is joined onto loopback, so
FORCE_SCRIPT_NAME comes off; the Project's Git repository is described to the Runtime only when
there is one; and each Runtime is given an application port of its own.
"""

from app_spark_api.agent.runtime.entities import AgentRuntimeHandle, GitRemote, LocalProcessConfig, StateCallback
from app_spark_api.agent.runtime.providers import local as local_mod
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


def _build_env(tmp_path, *, state_callback=None, git_remote=None, app_port=9000) -> dict[str, str]:
    """Build one Runtime's environment with everything but the varying part held fixed."""
    return _provider(tmp_path)._build_env(
        project_id="p",
        app_port=app_port,
        workspace_dir=tmp_path / "workspaces" / "p",
        state_dir=tmp_path / "state" / "c",
        runtime_token="runtime-token",
        state_callback=state_callback,
        git_remote=git_remote,
    )


def register_runtime(provider: LocalProcessProvider, conversation_id: str, *, app_port: int, alive: bool = True):
    """Put a Runtime in the provider's map without spawning anything."""

    class _Process:
        def poll(self):
            return None if alive else 0

    provider._runtimes[conversation_id] = local_mod._LocalRuntime(
        handle=AgentRuntimeHandle(
            conversation_id=conversation_id,
            base_url="http://127.0.0.1:1",
            runtime_token="runtime-token",
        ),
        process=_Process(),
        workspace_dir=provider.workspace_dir("p"),
        log_path=provider.state_dir(conversation_id),
        app_port=app_port,
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


def test_the_runtime_is_told_which_port_its_application_must_listen_on(tmp_path):
    """没有它，每个 Runtime 都会回落到 agent 自己的 8000，同一台机器上的第二个会话就拉不起应用。"""
    env = _build_env(tmp_path, app_port=9111)

    assert env[f"{ENV_PREFIX}APP_PORT"] == "9111"


def test_the_runtime_is_told_exactly_these_things_and_nothing_else(tmp_path):
    """锁住注入的整个键集合，而不是扫某个名字。

    要守的是「沙箱不知道自己被外面怎么寻址」——能打开的地址由控制面签发，沙箱知道了就会把它写进
    模型看得见的地方。按名字扫 PREVIEW 守不住这条：换个名字叫 PUBLIC_APP_URL 就漏过去了。锁住
    集合则是每加一项都得有人在这里承认一次。
    """
    env = _build_env(tmp_path)

    assert {name for name in env if name.startswith(ENV_PREFIX)} == {
        f"{ENV_PREFIX}WORKSPACE",
        f"{ENV_PREFIX}STATE_DIR",
        f"{ENV_PREFIX}RUNTIME_TOKEN",
        f"{ENV_PREFIX}PROJECT_ID",
        f"{ENV_PREFIX}APP_PORT",
    }


async def test_two_conversations_are_proxied_to_their_own_applications(tmp_path):
    provider = _provider(tmp_path)
    register_runtime(provider, "first", app_port=9001)
    register_runtime(provider, "second", app_port=9002)

    assert await provider.preview_upstream("first") == "http://127.0.0.1:9001"
    assert await provider.preview_upstream("second") == "http://127.0.0.1:9002"


async def test_a_conversation_nobody_ever_served_has_nothing_to_proxy_to(tmp_path):
    assert await _provider(tmp_path).preview_upstream("unknown") is None


async def test_a_conversation_whose_runtime_died_has_nothing_to_proxy_to(tmp_path):
    """端口号还记着，但那个进程已经没了，转过去只会连到别人手上的同号端口。"""
    provider = _provider(tmp_path)
    register_runtime(provider, "dead", app_port=9003, alive=False)

    assert await provider.preview_upstream("dead") is None


def test_the_two_ports_of_one_runtime_are_never_the_same(tmp_path):
    """应用端口要等模型调 launch_app 才被 bind，在那之前 _free_port 会把它再发一次。

    自己撞上自己的后果尤其难查：launch 会报「端口被本监督器之外的进程占了」，而占着它的其实
    是同一个 Runtime 的 agent 进程。
    """
    port, app_port = _provider(tmp_path)._reserve_ports()

    assert port != app_port


def test_an_application_port_already_handed_out_is_not_handed_out_again(tmp_path, monkeypatch):
    """同一台机器上的下一个 Runtime 抽到同号，两个应用里后启动的那个必败。"""
    provider = _provider(tmp_path)
    register_runtime(provider, "first", app_port=9101)

    # 让抽签先重复吐出已经发出去的那个号，逼出重抽这条路。
    draws = iter([9101, 9101, 9102, 9103])
    monkeypatch.setattr(local_mod, "_free_port", lambda: next(draws))

    assert provider._reserve_ports() == (9102, 9103)
