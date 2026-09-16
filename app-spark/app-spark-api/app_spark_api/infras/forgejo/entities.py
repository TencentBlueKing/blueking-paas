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

"""Connection settings and Forgejo API payloads the HTTP client understands."""

from __future__ import annotations

from typing import Any

import attrs

from app_spark_api.infras.forgejo.exceptions import ForgejoUnavailableError

_DEFAULT_BRANCH = "main"


@attrs.frozen
class ForgejoClientConfig:
    """How to reach one Forgejo HTTP API as a service account.

    Token create/delete need Basic Auth (username + password), not another token.

    :param base_url: Forgejo HTTP root.
    :param username: Service-account login used for Basic Auth.
    :param password: That account's password; never logged.
    :param timeout_seconds: HTTP timeout for API calls.
    """

    base_url: str
    username: str
    password: str = attrs.field(repr=False)
    timeout_seconds: float = 30.0


@attrs.frozen
class RemoteRepository:
    """A repository as Forgejo described it."""

    remote_id: int
    owner: str
    name: str
    default_branch: str
    private: bool

    @classmethod
    def from_payload(cls, payload: Any) -> RemoteRepository:
        if not isinstance(payload, dict):
            raise ForgejoUnavailableError(f"Expected a repository object, got {payload!r}")
        try:
            owner = payload["owner"]
            owner_name = owner["login"] if isinstance(owner, dict) else owner
            return cls(
                remote_id=int(payload["id"]),
                owner=str(owner_name),
                name=str(payload["name"]),
                default_branch=str(payload.get("default_branch") or _DEFAULT_BRANCH),
                private=bool(payload["private"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ForgejoUnavailableError(f"Unreadable repository response: {exc}") from exc


@attrs.frozen
class AccessToken:
    """A Forgejo access token. ``sha1`` is present only on create."""

    token_id: int
    name: str
    sha1: str | None = attrs.field(default=None, repr=False)

    @classmethod
    def from_payload(cls, payload: Any) -> AccessToken:
        if not isinstance(payload, dict):
            raise ForgejoUnavailableError(f"Expected a token object, got {payload!r}")
        try:
            sha1 = payload.get("sha1")
            return cls(
                token_id=int(payload["id"]),
                name=str(payload["name"]),
                sha1=None if sha1 is None else str(sha1),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ForgejoUnavailableError(f"Unreadable token response: {exc}") from exc
