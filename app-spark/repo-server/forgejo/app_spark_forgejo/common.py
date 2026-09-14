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

"""Shared helpers for the Forgejo admin CLI.

Used by local/dev Compose (``just start``) and later by a production init Job
against a chart-deployed Forgejo. HTTP calls are deployment-agnostic. The
Forgejo CLI wrapper defaults to ``docker compose exec``; override ``FORGEJO_CLI``
when the process already *is* the server (the chart init Job).
"""

from __future__ import annotations

import json
import os
import secrets
import shlex
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

FORGEJO_DIR = Path(__file__).resolve().parents[1]

ADMIN_USERNAME = "app-spark-admin"
ADMIN_EMAIL = "app-spark-admin@localhost.invalid"
SERVICE_USERNAME = "app-spark-bot"
SERVICE_EMAIL = "app-spark-bot@localhost.invalid"
ORG_NAME = "app-spark"
DEFAULT_BRANCH = "main"


def require_bin(name: str) -> str:
    """Resolve ``name`` on PATH. Ruff S607 wants an absolute executable."""
    path = shutil.which(name)
    if path is None:
        raise SystemExit(f"{name} is required on PATH")
    return path


def require_http_url(url: str) -> str:
    """Reject non-HTTP URLs before handing them to urllib (S310)."""
    if not url.startswith(("http://", "https://")):
        raise SystemExit(f"refusing non-HTTP URL: {url}")
    return url


def secrets_dir() -> Path:
    """Directory that holds generated passwords. Never log its contents."""
    configured = os.environ.get("FORGEJO_SECRETS_DIR")
    path = Path(configured) if configured else FORGEJO_DIR / "secrets"
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    return path


def credentials_path() -> Path:
    return secrets_dir() / "credentials.env"


def base_url() -> str:
    return os.environ.get("FORGEJO_ROOT_URL", "http://127.0.0.1:3000").rstrip("/")


def compose_env() -> dict[str, str]:
    """Environment for `docker compose` so test/dev projects stay distinct."""
    env = os.environ.copy()
    env.setdefault("COMPOSE_PROJECT_NAME", "app-spark-forgejo")
    env.setdefault("FORGEJO_HTTP_PORT", "3000")
    env.setdefault("FORGEJO_ROOT_URL", base_url())
    return env


def compose(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [require_bin("docker"), "compose", *args],
        cwd=FORGEJO_DIR,
        env=compose_env(),
        check=check,
        text=True,
        capture_output=True,
    )


def forgejo_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Run a `forgejo` CLI command inside the server process.

    Local/dev: ``docker compose exec``. Production: set ``FORGEJO_CLI`` to the
    in-process binary (for example ``forgejo``) so the same argv works in an
    init Job. Passwords are not included in *args.
    """
    override = os.environ.get("FORGEJO_CLI", "").strip()
    if override:
        return subprocess.run(
            [*shlex.split(override), *args],
            cwd=FORGEJO_DIR,
            env=os.environ.copy(),
            check=False,
            text=True,
            capture_output=True,
        )
    return compose("exec", "-T", "--user", "git", "server", "forgejo", *args, check=False)


def credentials_from_env() -> dict[str, str] | None:
    """Passwords injected by the environment (k8s Secret / CI), not a local file."""
    admin = os.environ.get("FORGEJO_ADMIN_PASSWORD", "").strip()
    service = os.environ.get("FORGEJO_SERVICE_ACCOUNT_PASSWORD", "").strip()
    if admin and service:
        return {"ADMIN_PASSWORD": admin, "SERVICE_ACCOUNT_PASSWORD": service}
    return None


def load_or_create_credentials() -> dict[str, str]:
    """Return service passwords: env first (production), else a local secrets file.

    Repeat init must reuse the same passwords: recreating users is skipped when
    they already exist, and the API service needs a stable service-account password.
    """
    from_env = credentials_from_env()
    if from_env is not None:
        return from_env
    path = credentials_path()
    values: dict[str, str] = {}
    if path.exists():
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key] = value
    changed = False
    for key in ("ADMIN_PASSWORD", "SERVICE_ACCOUNT_PASSWORD"):
        if not values.get(key):
            values[key] = secrets.token_urlsafe(24)
            changed = True
    if changed:
        body = (
            "# Generated by app-spark-forgejo init. Do not commit.\n"
            f"ADMIN_USERNAME={ADMIN_USERNAME}\n"
            f"ADMIN_PASSWORD={values['ADMIN_PASSWORD']}\n"
            f"SERVICE_ACCOUNT_USERNAME={SERVICE_USERNAME}\n"
            f"SERVICE_ACCOUNT_PASSWORD={values['SERVICE_ACCOUNT_PASSWORD']}\n"
            f"ORG_NAME={ORG_NAME}\n"
        )
        path.write_text(body)
        path.chmod(0o600)
    return values


def request_json(
    method: str,
    path: str,
    *,
    username: str,
    password: str,
    payload: dict[str, Any] | None = None,
    token: str | None = None,
    timeout: float = 30.0,
) -> tuple[int, Any]:
    """Call the Forgejo HTTP API. Passwords are not logged."""
    url = require_http_url(f"{base_url()}{path}")
    data = None if payload is None else json.dumps(payload).encode()
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    if token:
        req.add_header("Authorization", f"token {token}")
    else:
        import base64

        raw = f"{username}:{password}".encode()
        req.add_header("Authorization", "Basic " + base64.b64encode(raw).decode())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read()
            parsed: Any = json.loads(body) if body else None
            return response.status, parsed
    except urllib.error.HTTPError as exc:
        body = exc.read()
        try:
            parsed = json.loads(body) if body else None
        except json.JSONDecodeError:
            parsed = body.decode(errors="replace")
        return exc.code, parsed


def wait_ready(*, timeout_seconds: float = 120.0) -> None:
    """Block until ``/api/healthz`` answers 200, or raise.

    ``REQUIRE_SIGNIN_VIEW`` makes ``/api/v1/version`` return 403 even though
    the process is up. The health endpoint stays public.
    """
    deadline = time.monotonic() + timeout_seconds
    last_error = "no attempt"
    url = require_http_url(f"{base_url()}/api/healthz")
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if response.status == 200:
                    return
                last_error = f"HTTP {response.status}"
        except urllib.error.HTTPError as exc:
            last_error = f"HTTP {exc.code}"
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = str(exc)
        time.sleep(1)
    raise SystemExit(f"Forgejo at {base_url()} was not ready: {last_error}")
