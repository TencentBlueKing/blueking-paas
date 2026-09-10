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

"""Dev-mode acceptance: server-side invariants against a running Forgejo."""

from __future__ import annotations

import base64
import os
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from app_spark_forgejo.common import (
    DEFAULT_BRANCH,
    FORGEJO_DIR,
    ORG_NAME,
    SERVICE_USERNAME,
    base_url,
    compose,
    compose_env,
    forgejo_cli,
    load_or_create_credentials,
    request_json,
    require_bin,
    require_http_url,
    wait_ready,
)
from app_spark_forgejo.init import initialise

VERIFY_REPO = "phase1-verify"


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def ok(message: str) -> None:
    print(f"ok: {message}")


def _basic(username: str, secret: str) -> str:
    return "Basic " + base64.b64encode(f"{username}:{secret}".encode()).decode()


def ensure_private_repo(password: str) -> dict[str, Any]:
    status, body = request_json(
        "POST",
        f"/api/v1/orgs/{ORG_NAME}/repos",
        username=SERVICE_USERNAME,
        password=password,
        payload={
            "name": VERIFY_REPO,
            "private": True,
            "auto_init": True,
            "default_branch": DEFAULT_BRANCH,
            "description": "Phase-1 acceptance fixture",
        },
    )
    if status == 201 and isinstance(body, dict):
        return body
    if status in {409, 422}:
        got, existing = request_json(
            "GET",
            f"/api/v1/repos/{ORG_NAME}/{VERIFY_REPO}",
            username=SERVICE_USERNAME,
            password=password,
        )
        if got == 200 and isinstance(existing, dict):
            return existing
    fail(f"creating verify repo failed: HTTP {status} {body}")
    raise AssertionError  # unreachable, keeps type checkers happy


def ensure_branch_protection(password: str) -> None:
    payload = {
        "rule_name": DEFAULT_BRANCH,
        "enable_push": True,
        "enable_force_push": False,
        "enable_force_push_allowlist": False,
    }
    status, body = request_json(
        "POST",
        f"/api/v1/repos/{ORG_NAME}/{VERIFY_REPO}/branch_protections",
        username=SERVICE_USERNAME,
        password=password,
        payload=payload,
    )
    if status in {201, 200}:
        return
    if status in {403, 404, 409, 422}:
        # Already protected, or this Forgejo wants PATCH on an existing rule.
        patch, _ = request_json(
            "PATCH",
            f"/api/v1/repos/{ORG_NAME}/{VERIFY_REPO}/branch_protections/{DEFAULT_BRANCH}",
            username=SERVICE_USERNAME,
            password=password,
            payload=payload,
        )
        if patch in {200, 201}:
            return
    fail(f"branch protection failed: HTTP {status} {body}")


def issue_write_token(password: str) -> str:
    status, body = request_json(
        "POST",
        f"/api/v1/users/{SERVICE_USERNAME}/tokens",
        username=SERVICE_USERNAME,
        password=password,
        payload={
            "name": "phase1-verify-write",
            "scopes": ["write:repository"],
            "repositories": [{"owner": ORG_NAME, "name": VERIFY_REPO}],
        },
    )
    if status == 201 and isinstance(body, dict) and isinstance(body.get("sha1"), str):
        return body["sha1"]
    # Forgejo 15 reports a duplicate token name as HTTP 400, not 409/422.
    name_taken = status in {400, 409, 422}
    if name_taken:
        request_json(
            "DELETE",
            f"/api/v1/users/{SERVICE_USERNAME}/tokens/phase1-verify-write",
            username=SERVICE_USERNAME,
            password=password,
        )
        status, body = request_json(
            "POST",
            f"/api/v1/users/{SERVICE_USERNAME}/tokens",
            username=SERVICE_USERNAME,
            password=password,
            payload={
                "name": "phase1-verify-write",
                "scopes": ["write:repository"],
                "repositories": [{"owner": ORG_NAME, "name": VERIFY_REPO}],
            },
        )
        if status == 201 and isinstance(body, dict) and isinstance(body.get("sha1"), str):
            return body["sha1"]
    fail(f"issuing write token failed: HTTP {status} {body}")
    raise AssertionError


def git(*args: str, cwd: Path, token: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_ASKPASS"] = "true"
    env["GIT_CONFIG_COUNT"] = "1"
    env["GIT_CONFIG_KEY_0"] = "commit.gpgsign"
    env["GIT_CONFIG_VALUE_0"] = "false"
    header = f"Authorization: {_basic(SERVICE_USERNAME, token)}"
    return subprocess.run(
        [require_bin("git"), "-c", f"http.extraHeader={header}", *args],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def clone_url(repo: str = VERIFY_REPO) -> str:
    return f"{base_url()}/{ORG_NAME}/{repo}.git"


def first_push(token: str) -> Path:
    work = Path(tempfile.mkdtemp(prefix="forgejo-verify-"))
    cloned = git("clone", clone_url(), str(work / "repo"), cwd=work, token=token)
    if cloned.returncode != 0:
        fail(f"clone failed: {cloned.stderr}")
    repo = work / "repo"
    (repo / "phase1.txt").write_text(f"phase-1 {os.urandom(8).hex()}\n")
    for cmd in (
        ["config", "user.name", "App-Spark"],
        ["config", "user.email", "app-spark@localhost.invalid"],
        ["add", "phase1.txt"],
        ["commit", "-m", "phase-1 verify"],
        ["push", "origin", DEFAULT_BRANCH],
    ):
        result = git(*cmd, cwd=repo, token=token)
        if result.returncode != 0:
            fail(f"git {' '.join(cmd)} failed: {result.stderr or result.stdout}")
    return repo


def assert_force_push_rejected(repo: Path, token: str) -> None:
    amend = git("commit", "--amend", "-m", "rewritten history", cwd=repo, token=token)
    if amend.returncode != 0:
        fail(f"amend failed: {amend.stderr}")
    pushed = git("push", "--force", "origin", DEFAULT_BRANCH, cwd=repo, token=token)
    if pushed.returncode == 0:
        fail("force push succeeded; branch protection is not holding")
    ok("force push is rejected")


def assert_push_create_disabled(token: str) -> None:
    work = Path(tempfile.mkdtemp(prefix="forgejo-push-create-"))
    git_env = {
        **os.environ,
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "commit.gpgsign",
        "GIT_CONFIG_VALUE_0": "false",
    }
    git_bin = require_bin("git")
    subprocess.run(
        [git_bin, "init", "-b", DEFAULT_BRANCH],
        cwd=work,
        check=True,
        capture_output=True,
        env=git_env,
    )
    (work / "README").write_text("no\n")
    for cmd in (
        ["config", "user.name", "App-Spark"],
        ["config", "user.email", "app-spark@localhost.invalid"],
        ["add", "README"],
        ["commit", "-m", "should not create a repo"],
        ["remote", "add", "origin", clone_url("does-not-exist-repo")],
    ):
        subprocess.run([git_bin, *cmd], cwd=work, check=True, capture_output=True, env=git_env)
    pushed = git("push", "-u", "origin", DEFAULT_BRANCH, cwd=work, token=token)
    if pushed.returncode == 0:
        fail("push to a missing repository name created one; ENABLE_PUSH_CREATE_* must stay off")
    ok("push to a missing repository name fails")


def assert_basic_auth_git(password: str) -> None:
    result = git("ls-remote", clone_url(), cwd=Path.cwd(), token=password)
    if result.returncode != 0:
        fail(f"service account Basic Auth git failed: {result.stderr}")
    ok("service account can use Basic Auth for Git HTTP")


def assert_repo_is_private(repo_body: dict[str, Any]) -> None:
    if repo_body.get("private") is not True:
        fail(f"verify repo is not private: {repo_body.get('private')!r}")
    url = require_http_url(f"{base_url()}/api/v1/repos/{ORG_NAME}/{VERIFY_REPO}")
    try:
        urllib.request.urlopen(url, timeout=10)
        fail("anonymous API access to the private repository succeeded")
    except urllib.error.HTTPError as exc:
        if exc.code not in {401, 403, 404}:
            fail(f"anonymous access returned HTTP {exc.code}, expected 401/403/404")
    ok("new repository is private and anonymous access is refused")


def assert_container_can_reach(token: str) -> None:
    url = f"http://server:3000/{ORG_NAME}/{VERIFY_REPO}.git"
    header = f"Authorization: {_basic(SERVICE_USERNAME, token)}"
    env = compose_env()
    result = subprocess.run(
        [
            require_bin("docker"),
            "compose",
            "run",
            "--rm",
            "--no-deps",
            "-e",
            "GIT_TERMINAL_PROMPT=0",
            "--entrypoint",
            "git",
            "git-client",
            "-c",
            "http.sslVerify=false",
            "-c",
            f"http.extraHeader={header}",
            "ls-remote",
            url,
        ],
        cwd=FORGEJO_DIR,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        fail(f"git-client container could not reach Forgejo: {result.stderr or result.stdout}")
    ok(f"container on the Compose network can reach Git HTTP ({url})")


def assert_repeat_init_is_idempotent() -> None:
    before = forgejo_cli("admin", "user", "list")
    if before.returncode != 0:
        fail(f"listing users failed: {before.stderr}")
    initialise()
    after = forgejo_cli("admin", "user", "list")
    if before.stdout.count("\n") != after.stdout.count("\n"):
        fail("repeat init created extra users")
    ok("repeat init does not create duplicate accounts")


def assert_restart_keeps_repo(password: str) -> None:
    stopped = compose("stop", "server")
    if stopped.returncode != 0:
        fail(f"stop failed: {stopped.stderr}")
    started = compose("up", "-d", "server")
    if started.returncode != 0:
        fail(f"start failed: {started.stderr}")
    wait_ready()
    status, body = request_json(
        "GET",
        f"/api/v1/repos/{ORG_NAME}/{VERIFY_REPO}",
        username=SERVICE_USERNAME,
        password=password,
    )
    if status != 200:
        fail(f"repository missing after restart: HTTP {status} {body}")
    ok("repository still exists after restart")


def verify() -> None:
    require_bin("git")
    wait_ready()
    creds = load_or_create_credentials()
    password = creds["SERVICE_ACCOUNT_PASSWORD"]
    repo_body = ensure_private_repo(password)
    if repo_body.get("private") is not True:
        fail("Forgejo created a non-private repository")
    ensure_branch_protection(password)
    token = issue_write_token(password)
    work_repo = first_push(token)
    ok("host can clone and push")
    assert_force_push_rejected(work_repo, token)
    assert_push_create_disabled(token)
    assert_basic_auth_git(password)
    assert_repo_is_private(repo_body)
    assert_container_can_reach(token)
    assert_repeat_init_is_idempotent()
    assert_restart_keeps_repo(password)
    print("phase-1 verification passed")
