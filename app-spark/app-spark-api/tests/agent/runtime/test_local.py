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

"""local_process joins the public callback path onto loopback, so FORCE_SCRIPT_NAME comes off."""

from app_spark_api.agent.runtime.entities import LocalProcessConfig, StateCallback
from app_spark_api.agent.runtime.providers.local import ENV_PREFIX, LocalProcessProvider

PUBLIC_PATH = "/api-svc/api/internal/conversations/x/state/"
PATH_INFO = "/api/internal/conversations/x/state/"


def _provider(tmp_path) -> LocalProcessProvider:
    return LocalProcessProvider(
        LocalProcessConfig(
            agent_project_dir="/srv/agent",
            workspace_root=str(tmp_path / "workspaces"),
            state_root=str(tmp_path / "state"),
            callback_base_url="http://127.0.0.1:8000",
        )
    )


def test_local_process_strips_force_script_name_from_the_callback(settings, tmp_path):
    settings.FORCE_SCRIPT_NAME = "/api-svc"
    env = _provider(tmp_path)._build_env(
        workspace_dir=tmp_path / "workspaces" / "p",
        state_dir=tmp_path / "state" / "c",
        runtime_token="runtime-token",
        state_callback=StateCallback(path=PUBLIC_PATH, token="callback-token"),
    )

    assert env[f"{ENV_PREFIX}CONTROL_PLANE_URL"] == f"http://127.0.0.1:8000{PATH_INFO}"


def test_local_process_keeps_an_unprefixed_callback_path(tmp_path):
    env = _provider(tmp_path)._build_env(
        workspace_dir=tmp_path / "workspaces" / "p",
        state_dir=tmp_path / "state" / "c",
        runtime_token="runtime-token",
        state_callback=StateCallback(path=PATH_INFO, token="callback-token"),
    )

    assert env[f"{ENV_PREFIX}CONTROL_PLANE_URL"] == f"http://127.0.0.1:8000{PATH_INFO}"
