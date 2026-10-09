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

"""The ``APP_SPARK_AGENT_*`` variables every provider hands to the Runtime it starts."""

from app_spark_api.agent.runtime.constants import ENV_PREFIX
from app_spark_api.agent.runtime.entities import (
    BkAidevModelAccess,
    DirectModelAccess,
    GitRemote,
    ModelAccess,
    StateCallback,
)


def build_agent_env(
    *,
    workspace: str,
    state_dir: str,
    runtime_token: str,
    project_id: str,
    app_port: int,
    model_access: ModelAccess,
    extra_env: dict[str, str] | None = None,
    port: int | None = None,
    control_plane_url: str | None = None,
    state_callback: StateCallback | None = None,
    git_remote: GitRemote | None = None,
) -> dict[str, str]:
    """Build the Agent's own configuration, independent of where the Runtime runs.

    Where the Runtime is started decides what surrounds these: the local provider adds an
    allow-listed part of its own environment, a sandbox adds nothing.

    Example::

        env = build_agent_env(
            workspace="/data/workspace",
            state_dir="/data/state",
            runtime_token=token,
            project_id="p-1",
            app_port=9000,
            model_access=DirectModelAccess(model="fake:write-file"),
        )

    :param workspace: The Agent's workspace directory.
    :param state_dir: The Agent's durable state directory.
    :param runtime_token: Bearer the Runtime requires on every endpoint.
    :param project_id: Project the Runtime works on.
    :param app_port: Port the workspace application is launched on.
    :param model_access: How the Runtime calls its model.
    :param extra_env: Further ``APP_SPARK_AGENT_*`` variables, already validated by the config.
    :param port: Port the Runtime listens on. Omitted when the caller tells the server its port
        on the command line instead.
    :param control_plane_url: Full state replication URL as reachable from the Runtime. Given
        together with ``state_callback``; the caller decides whether the public prefix stays.
    :param state_callback: Replication token source; ignored without ``control_plane_url``.
    :param git_remote: Where the Runtime persists its workspace.
    :return: Variable names mapped to values.
    """
    env = {
        "WORKSPACE": workspace,
        "STATE_DIR": state_dir,
        "RUNTIME_TOKEN": runtime_token,
        "PROJECT_ID": project_id,
        # Not left to the agent's own default: on a shared host that default is the same number
        # for every conversation, and in a sandbox it collides with the Runtime's own port.
        "APP_PORT": str(app_port),
    }
    if port is not None:
        env["PORT"] = str(port)

    if control_plane_url is not None and state_callback is not None:
        # An address already scoped to one conversation, plus a token that authorizes only
        # that one. Deliberately all the Runtime learns: it replicates to a URL it was
        # handed, and never has to know what a conversation is or which one it is serving.
        env["CONTROL_PLANE_URL"] = control_plane_url
        env["CONTROL_PLANE_TOKEN"] = state_callback.token

    if git_remote is not None:
        # Absent these the Runtime keeps its workspace on local disk and says so on
        # `/health`; it does not quietly behave as though the files were being saved.
        env["GIT_REMOTE_URL"] = git_remote.clone_url
        env["GIT_BRANCH"] = git_remote.branch
        env["GIT_USERNAME"] = git_remote.username
        env["GIT_TOKEN"] = git_remote.token

    env.update(build_model_env(model_access))
    # extra_env 的键已经是 APP_SPARK_AGENT_*，不参加上面的加前缀。摊在前面：同名时以本函数
    # 为准，调用方只能追加变量，不能换掉身份、路径或 Bearer。
    return {**(extra_env or {}), **_add_env_prefix(env)}


def _add_env_prefix(env: dict[str, str]) -> dict[str, str]:
    """Prefix each name with APP_SPARK_AGENT_."""

    return {f"{ENV_PREFIX}{name}": value for name, value in env.items()}


def build_model_env(model_access: ModelAccess) -> dict[str, str]:
    """Return this source's model variables, named without the agent prefix."""

    # 模型变量只能从这里来：继承的环境是白名单，extra_env 也拒绝它们。
    match model_access:
        # 直连厂商：固定 key。fake: 模型不需要 key，就不给。
        case DirectModelAccess(model=model, api_key=api_key):
            env = {"MODEL": model}
            if api_key is not None:
                env["MODEL_API_KEY"] = api_key
            return env

        # bkaidev：只有用户态 access_token。不给 MODEL_API_KEY，agent 缺 token 时会回落到它，
        # 那就成了用共享密钥冒充用户。
        case BkAidevModelAccess(base_url=base_url, model_name=model_name, access_token=access_token):
            return {
                "BK_AIDEV_ACCESS_TOKEN": access_token,
                "MODEL_BASE_URL": base_url,
                "MODEL_NAME": model_name,
            }
