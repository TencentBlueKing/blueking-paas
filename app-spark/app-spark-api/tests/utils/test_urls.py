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

from uuid import uuid4

from django.urls import reverse, set_script_prefix

from app_spark_api.agent.conversations.internal_api import APPEND_MESSAGES_URL_NAME, state_ingest_path
from app_spark_api.utils.urls import reverse_path_info, reverse_public, to_path_info

USERINFO_PATH = "/api/accounts/userinfo/"


def test_reverse_public_uses_force_script_name_from_settings(settings):
    settings.FORCE_SCRIPT_NAME = "/api-svc"

    assert reverse_public("api:accounts-userinfo") == f"/api-svc{USERINFO_PATH}"
    assert reverse_public("home") == "/api-svc/"


def test_reverse_public_does_not_double_an_existing_prefix(settings):
    settings.FORCE_SCRIPT_NAME = "/api-svc"
    set_script_prefix("/api-svc")
    try:
        assert reverse_public("api:accounts-userinfo") == f"/api-svc{USERINFO_PATH}"
    finally:
        set_script_prefix("/")


def test_reverse_path_info_strips_settings_and_thread_local_prefix(settings):
    conversation_id = uuid4()
    viewname = f"api:{APPEND_MESSAGES_URL_NAME}"
    kwargs = {"conversation_id": conversation_id}
    settings.FORCE_SCRIPT_NAME = "/api-svc"
    set_script_prefix("/api-svc")
    try:
        public_url = reverse(viewname, kwargs=kwargs)
        path_info = reverse_path_info(viewname, kwargs=kwargs)
    finally:
        set_script_prefix("/")

    assert public_url.startswith("/api-svc/")
    assert path_info == public_url.removeprefix("/api-svc")
    assert path_info.startswith("/api/")


def test_reverse_path_info_strips_thread_local_prefix_alone():
    conversation_id = uuid4()
    viewname = f"api:{APPEND_MESSAGES_URL_NAME}"
    kwargs = {"conversation_id": conversation_id}
    set_script_prefix("/api-svc")
    try:
        path_info = reverse_path_info(viewname, kwargs=kwargs)
    finally:
        set_script_prefix("/")

    assert path_info.startswith("/api/")
    assert not path_info.startswith("/api-svc/")


def test_state_ingest_path_includes_force_script_name(settings):
    conversation_id = uuid4()
    settings.FORCE_SCRIPT_NAME = "/api-svc"

    path = state_ingest_path(conversation_id)

    assert path.startswith(f"/api-svc/api/internal/conversations/{conversation_id}/")
    assert path.endswith("/state/")


def test_to_path_info_strips_force_script_name(settings):
    settings.FORCE_SCRIPT_NAME = "/api-svc"

    assert to_path_info("/api-svc/api/internal/conversations/x/state/") == "/api/internal/conversations/x/state/"


def test_to_path_info_leaves_unprefixed_paths_alone(settings):
    settings.FORCE_SCRIPT_NAME = "/api-svc"

    assert to_path_info("/api/internal/conversations/x/state/") == "/api/internal/conversations/x/state/"
