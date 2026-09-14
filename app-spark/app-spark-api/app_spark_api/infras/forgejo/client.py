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

"""A narrow Forgejo HTTP client. Not a general SDK: only the calls provision needs."""

from __future__ import annotations

import logging
from http import HTTPStatus
from typing import Any, Self
from uuid import uuid4

import httpx2

from app_spark_api.infras.forgejo.entities import AccessToken, ForgejoClientConfig, RemoteRepository
from app_spark_api.infras.forgejo.exceptions import ForgejoUnavailableError

# A probe file written with a read token must be refused; the name is not a real project file.
# 该探针文件将被写入到项目中，作为 token 读写能力测试的一部分。
_READ_PROBE_PATH = ".app-spark-read-token-probe"
logger = logging.getLogger(__name__)


class ForgejoClient:
    """Forgejo API v1, authenticated as the service account via Basic Auth.

    Token create/delete require username/password, not another token, which is why
    this client carries the service-account password rather than a management token.

    :param config: Connection settings for one Forgejo.
    :param transport: httpx transport; tests inject ``MockTransport``.
    """

    def __init__(
        self,
        config: ForgejoClientConfig,
        *,
        transport: httpx2.BaseTransport | None = None,
    ) -> None:
        self._config = config
        self._transport = transport
        self._client = httpx2.Client(
            base_url=config.base_url.rstrip("/") + "/",
            timeout=config.timeout_seconds,
            transport=transport,
            auth=(config.username, config.password),
            headers={"Accept": "application/json"},
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def get_repo(self, owner: str, name: str) -> RemoteRepository | None:
        """Return the repository, or ``None`` if it does not exist."""
        response = self._request("GET", f"api/v1/repos/{owner}/{name}")
        if response.status_code == HTTPStatus.NOT_FOUND:
            return None
        self._raise_for_status(response, f"GET repo {owner}/{name}")
        return RemoteRepository.from_payload(response.json())

    def create_org_repo(self, *, owner: str, name: str, default_branch: str) -> RemoteRepository:
        """Create a private repository in the organisation.

        ``private`` is forced true: a public repo would let any repo-scoped token
        read it (Forgejo grants those tokens read access to all public repos).
        """
        response = self._request(
            "POST",
            f"api/v1/orgs/{owner}/repos",
            json={
                "name": name,
                "private": True,
                "auto_init": True,
                "default_branch": default_branch,
                "description": f"App-Spark project {name}",
            },
        )
        if response.status_code in {HTTPStatus.CONFLICT, HTTPStatus.UNPROCESSABLE_ENTITY}:
            existing = self.get_repo(owner, name)
            if existing is not None:
                return existing
        self._raise_for_status(response, f"POST org repo {owner}/{name}")
        return RemoteRepository.from_payload(response.json())

    def ensure_private_repo(self, *, owner: str, name: str, default_branch: str) -> RemoteRepository:
        """Create the private repo, or attach to one that already exists.

        Idempotent: a lost create-response is recovered by GET. A repo that is
        public is a hard failure -- we will not use it.
        """
        existing = self.get_repo(owner, name)
        if existing is None:
            try:
                repo = self.create_org_repo(owner=owner, name=name, default_branch=default_branch)
            except ForgejoUnavailableError:
                # Create may have succeeded on the server while the body was lost.
                recovered = self.get_repo(owner, name)
                if recovered is None:
                    raise
                repo = recovered
        else:
            repo = existing
        if not repo.private:
            raise ForgejoUnavailableError(
                f"Repository {owner}/{name} is public; App-Spark repositories must stay private"
            )
        return repo

    def ensure_branch_protection(self, owner: str, name: str, branch: str) -> None:
        """Forbid force-push (and branch deletion) on the working branch.

        This is the server-side defence against a replaced Runtime pushing: its
        history is behind, so a non-fast-forward is rejected without knowing who
        it is. Protected branches also cannot be deleted.
        """
        payload = {
            "rule_name": branch,
            "enable_push": True,
            "enable_force_push": False,
            "enable_force_push_allowlist": False,
        }
        path = f"api/v1/repos/{owner}/{name}/branch_protections"
        # Forgejo 15 returns 403 both for an existing rule and for denied access.
        # Query first so a permission failure on create is never guessed away.
        existing = self._request("GET", f"{path}/{branch}")
        if existing.status_code == HTTPStatus.OK:
            response = self._request("PATCH", f"{path}/{branch}", json=payload)
            self._raise_for_status(response, f"PATCH branch protection {owner}/{name} {branch}")
            return
        if existing.status_code != HTTPStatus.NOT_FOUND:
            self._raise_for_status(existing, f"GET branch protection {owner}/{name} {branch}")
        response = self._request(
            "POST",
            path,
            json=payload,
        )
        if response.status_code in {HTTPStatus.CREATED, HTTPStatus.OK}:
            return
        if response.status_code in {HTTPStatus.CONFLICT, HTTPStatus.UNPROCESSABLE_ENTITY}:
            patch = self._request(
                "PATCH",
                f"api/v1/repos/{owner}/{name}/branch_protections/{branch}",
                json=payload,
            )
            if patch.status_code in {HTTPStatus.OK, HTTPStatus.CREATED}:
                return
            self._raise_for_status(patch, f"PATCH branch protection {owner}/{name} {branch}")
            return
        self._raise_for_status(response, f"POST branch protection {owner}/{name} {branch}")

    def create_token(
        self,
        *,
        name: str,
        scopes: list[str],
        owner: str,
        repo_name: str,
    ) -> AccessToken:
        """Create a repository-scoped token. The plaintext is on the response once."""
        response = self._request(
            "POST",
            f"api/v1/users/{self._config.username}/tokens",
            json={
                "name": name,
                "scopes": scopes,
                "repositories": [{"owner": owner, "name": repo_name}],
            },
        )
        self._raise_for_status(response, f"POST token {name}")
        token = AccessToken.from_payload(response.json())
        if not token.sha1:
            raise ForgejoUnavailableError(f"Token {name} was created without returning its secret")
        return token

    def delete_token(self, token_id: int) -> None:
        response = self._request(
            "DELETE",
            f"api/v1/users/{self._config.username}/tokens/{token_id}",
        )
        if response.status_code == HTTPStatus.NOT_FOUND:
            return
        self._raise_for_status(response, f"DELETE token {token_id}")

    def delete_tokens_named(self, name: str) -> None:
        """Drop the token of this name so a re-issue cannot collide.

        Forgejo token names are unique per user and DELETE accepts a name. Our
        generated names are nonnumeric, so they cannot be mistaken for an ID.
        No paginated account-wide list is needed to revoke a project's token.
        """
        response = self._request(
            "DELETE",
            f"api/v1/users/{self._config.username}/tokens/{name}",
        )
        if response.status_code not in {HTTPStatus.NO_CONTENT, HTTPStatus.OK, HTTPStatus.NOT_FOUND}:
            self._raise_for_status(response, f"DELETE token name {name}")

    def reissue_repo_token(
        self,
        *,
        name: str,
        scopes: list[str],
        owner: str,
        repo_name: str,
    ) -> AccessToken:
        """Revoke any token of this name, then create a new one.

        Needed when a previous create succeeded on Forgejo but the body never
        reached us: we cannot recover the plaintext, only throw the leftover away.
        """
        self.delete_tokens_named(name)
        return self.create_token(name=name, scopes=scopes, owner=owner, repo_name=repo_name)

    def verify_read_token_cannot_write(self, token: AccessToken, owner: str, repo_name: str) -> None:
        """Confirm a read-scoped token can see the repo and cannot change it.

        Uses the contents API rather than git(1): provision runs in the API
        process, which does not yet install Git (that is stage 3). Live tests
        still exercise clone/push with real git.

        The pinned Forgejo accepts GET with read:repository (HTTP 200) and
        rejects a contents POST (HTTP 403). A 403/404 on GET does not prove read
        access; a 404/409/422/5xx on POST does not prove write protection either.
        Keep these checks strict; verify other versions with the live Git tests.
        """
        if not token.sha1:
            raise ForgejoUnavailableError("read token has no secret to verify")
        with httpx2.Client(
            base_url=str(self._client.base_url),
            timeout=self._config.timeout_seconds,
            transport=self._transport,
            headers={"Authorization": f"token {token.sha1}", "Accept": "application/json"},
        ) as scoped:
            try:
                self._verify_read_token(scoped, owner, repo_name)
            except httpx2.HTTPError as exc:
                raise ForgejoUnavailableError(f"Read-token verification failed for {owner}/{repo_name}") from exc

    def _verify_read_token(self, scoped: httpx2.Client, owner: str, repo_name: str) -> None:
        seen = scoped.get(f"api/v1/repos/{owner}/{repo_name}")
        if seen.status_code != HTTPStatus.OK:
            raise ForgejoUnavailableError(f"read token could not GET {owner}/{repo_name}: HTTP {seen.status_code}")
        # A unique name avoids touching project files or mistaking a stale
        # probe's create conflict for evidence that writes are forbidden.
        path = f"api/v1/repos/{owner}/{repo_name}/contents/{_READ_PROBE_PATH}-{uuid4().hex}"
        probe = scoped.post(
            path,
            json={"content": "dGVzdA==", "message": "read-token probe"},
        )
        if probe.status_code < 400:
            self._cleanup_read_probe(path, probe)
            raise ForgejoUnavailableError(
                f"read token was allowed to write {owner}/{repo_name}: HTTP {probe.status_code}"
            )
        if probe.status_code != HTTPStatus.FORBIDDEN:
            raise ForgejoUnavailableError(
                f"read-token write check was inconclusive for {owner}/{repo_name}: HTTP {probe.status_code}"
            )

    def _cleanup_read_probe(self, path: str, probe: httpx2.Response) -> None:
        # Use the service account, whose write access does not depend on the
        # broken read-token restriction. Delete only the blob this probe wrote.
        # This leaves an ordinary cleanup commit; never rewrite project history.
        try:
            sha = probe.json()["content"]["sha"]
            response = self._request("DELETE", path, json={"sha": sha, "message": "remove read-token probe"})
            self._raise_for_status(response, "DELETE read-token probe")
        except ForgejoUnavailableError, ValueError, KeyError, TypeError:
            # Keep the permission violation as the primary failure even when
            # cleanup fails. Operators still get the complete cleanup error.
            logger.exception("Could not clean up read-token probe %s", path)

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx2.Response:
        try:
            return self._client.request(method, path, **kwargs)
        except httpx2.HTTPError as exc:
            raise ForgejoUnavailableError(f"Forgejo request {method} {path} failed: {exc}") from exc

    def _raise_for_status(self, response: httpx2.Response, action: str) -> None:
        if response.is_success:
            return
        raise ForgejoUnavailableError(f"{action} failed: HTTP {response.status_code} {response.text}")
