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

"""In-memory Forgejo used by unit tests through httpx ``MockTransport``."""

from __future__ import annotations

import json
import threading
from http import HTTPStatus
from typing import Any

import httpx2

from app_spark_api.infras.forgejo import ForgejoClient, ForgejoClientConfig

ORG = "app-spark"
SERVICE_ACCOUNT = "app-spark-bot"
SERVICE_PASSWORD = "service-password"


def repo_server_config(**overrides: Any) -> dict[str, Any]:
    """A complete ``REPO_SERVER`` mapping unit tests can put on Django settings."""
    payload = {
        "type": "forgejo",
        "base_url": "http://forgejo.invalid",
        "clone_url": "http://git-for-agent.invalid",
        "org": ORG,
        "service_account": SERVICE_ACCOUNT,
        "service_account_password": SERVICE_PASSWORD,
        "default_branch": "main",
        "commit_author_name": "App-Spark",
        "commit_author_email": "app-spark@localhost.invalid",
    }
    payload.update(overrides)
    return payload


def forgejo_client_config(**overrides: Any) -> ForgejoClientConfig:
    payload = {
        "base_url": "http://forgejo.invalid",
        "username": SERVICE_ACCOUNT,
        "password": SERVICE_PASSWORD,
    }
    payload.update(overrides)
    return ForgejoClientConfig(**payload)


class FakeForgejo:
    """Stateful stand-in for the Forgejo routes provision actually calls."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.repos: dict[tuple[str, str], dict[str, Any]] = {}
        self.tokens: dict[int, dict[str, Any]] = {}
        self.protections: set[tuple[str, str, str]] = set()
        self._next_repo_id = 1
        self._next_token_id = 1
        self.drop_next_create_response = False
        self.drop_next_token_response = False
        self.fail_next_request = False

    def client(self, config: ForgejoClientConfig | None = None) -> ForgejoClient:
        resolved = config if isinstance(config, ForgejoClientConfig) else forgejo_client_config()
        return ForgejoClient(resolved, transport=httpx2.MockTransport(self._handle))

    def _handle(self, request: httpx2.Request) -> httpx2.Response:
        if self.fail_next_request:
            self.fail_next_request = False
            raise httpx2.ConnectError("connection refused")
        path = request.url.path
        method = request.method
        body = json.loads(request.content) if request.content else {}
        with self._lock:
            return self._dispatch(method, path, body, request)

    def _dispatch(  # noqa: PLR0911
        self,
        method: str,
        path: str,
        body: dict[str, Any],
        request: httpx2.Request,
    ) -> httpx2.Response:
        parts = [p for p in path.split("/") if p]
        # /api/v1/...
        if parts[:2] != ["api", "v1"]:
            return self._json(HTTPStatus.NOT_FOUND, {"message": "no such route"})

        rest = parts[2:]
        if method == "GET" and rest[:1] == ["repos"] and len(rest) == 3:
            return self._get_repo(rest[1], rest[2], request)
        if method == "POST" and rest[:1] == ["orgs"] and rest[-1:] == ["repos"]:
            return self._create_repo(rest[1], body)
        if method == "POST" and len(rest) == 4 and rest[0] == "repos" and rest[3] == "branch_protections":
            return self._protect(rest[1], rest[2], body)
        if method == "PATCH" and len(rest) == 5 and rest[0] == "repos" and rest[3] == "branch_protections":
            return self._protect(rest[1], rest[2], body, branch=rest[4])
        if method == "GET" and rest[:1] == ["users"] and rest[-1:] == ["tokens"]:
            return self._list_tokens()
        if method == "POST" and rest[:1] == ["users"] and rest[-1:] == ["tokens"]:
            return self._create_token(body)
        if method == "DELETE" and rest[:1] == ["users"] and rest[-2:-1] == ["tokens"]:
            return self._delete_token(rest[-1])
        if method == "POST" and len(rest) >= 5 and rest[0] == "repos" and rest[3] == "contents":
            return self._write_contents(request)
        return self._json(HTTPStatus.NOT_FOUND, {"message": f"unhandled {method} {path}"})

    def _auth_token(self, request: httpx2.Request) -> str | None:
        header = request.headers.get("authorization", "")
        if header.lower().startswith("token "):
            return header.split(" ", 1)[1]
        return None

    def _get_repo(self, owner: str, name: str, request: httpx2.Request) -> httpx2.Response:
        token = self._auth_token(request)
        if token:
            found = next((t for t in self.tokens.values() if t["sha1"] == token), None)
            if found is None:
                return self._json(HTTPStatus.UNAUTHORIZED, {"message": "bad token"})
            allowed = {(r["owner"], r["name"]) for r in found["repositories"]}
            if (owner, name) not in allowed:
                return self._json(HTTPStatus.NOT_FOUND, {"message": "not found"})
        repo = self.repos.get((owner, name))
        if repo is None:
            return self._json(HTTPStatus.NOT_FOUND, {"message": "not found"})
        return self._json(HTTPStatus.OK, repo)

    def _create_repo(self, owner: str, body: dict[str, Any]) -> httpx2.Response:
        name = str(body["name"])
        key = (owner, name)
        if key in self.repos:
            return self._json(HTTPStatus.CONFLICT, {"message": "exist"})
        repo = {
            "id": self._next_repo_id,
            "name": name,
            "owner": {"login": owner},
            "private": bool(body.get("private", False)),
            "default_branch": body.get("default_branch", "main"),
        }
        self._next_repo_id += 1
        self.repos[key] = repo
        if self.drop_next_create_response:
            self.drop_next_create_response = False
            return self._json(HTTPStatus.GATEWAY_TIMEOUT, {"message": "lost"})
        return self._json(HTTPStatus.CREATED, repo)

    def _protect(self, owner: str, name: str, body: dict[str, Any], branch: str | None = None) -> httpx2.Response:
        rule = branch or str(body.get("rule_name") or "main")
        key = (owner, name, rule)
        existed = key in self.protections
        if existed and branch is None:
            return self._json(HTTPStatus.CONFLICT, {"message": "exist"})
        self.protections.add(key)
        status = HTTPStatus.OK if existed else HTTPStatus.CREATED
        return self._json(status, {"rule_name": rule, "enable_force_push": False})

    def _list_tokens(self) -> httpx2.Response:
        listed = [{"id": t["id"], "name": t["name"], "sha1": None} for t in self.tokens.values()]
        return self._json(HTTPStatus.OK, listed)

    def _create_token(self, body: dict[str, Any]) -> httpx2.Response:
        name = str(body["name"])
        if any(t["name"] == name for t in self.tokens.values()):
            return self._json(HTTPStatus.UNPROCESSABLE_ENTITY, {"message": "token name already used"})
        token_id = self._next_token_id
        self._next_token_id += 1
        sha1 = f"tok-{token_id}-{name}"
        record = {
            "id": token_id,
            "name": name,
            "sha1": sha1,
            "scopes": list(body.get("scopes") or []),
            "repositories": list(body.get("repositories") or []),
        }
        self.tokens[token_id] = record
        if self.drop_next_token_response:
            self.drop_next_token_response = False
            return self._json(HTTPStatus.GATEWAY_TIMEOUT, {"message": "lost"})
        return self._json(HTTPStatus.CREATED, record)

    def _delete_token(self, ident: str) -> httpx2.Response:
        if ident.isdigit():
            self.tokens.pop(int(ident), None)
            return httpx2.Response(HTTPStatus.NO_CONTENT)
        for token_id, token in list(self.tokens.items()):
            if token["name"] == ident:
                del self.tokens[token_id]
        return httpx2.Response(HTTPStatus.NO_CONTENT)

    def _write_contents(self, request: httpx2.Request) -> httpx2.Response:
        token = self._auth_token(request)
        found = next((t for t in self.tokens.values() if t["sha1"] == token), None)
        if found is None:
            return self._json(HTTPStatus.UNAUTHORIZED, {"message": "bad token"})
        if "write:repository" not in found["scopes"]:
            return self._json(HTTPStatus.FORBIDDEN, {"message": "read only"})
        return self._json(HTTPStatus.CREATED, {"content": {}})

    def _json(self, status: HTTPStatus, payload: Any) -> httpx2.Response:
        return httpx2.Response(status, json=payload)
