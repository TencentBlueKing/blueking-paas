"""A real Git host for the workspace component, provisioned the way production provisions one.

Not collected unless ``APP_SPARK_FORGEJO_LIVE=1``. When it is, this starts the sibling
``repo-server/forgejo`` test instance (``just test-up``) exactly as the API's own live tests do,
and a Forgejo that will not start **fails** the job rather than skipping it -- a persistence
feature whose only end-to-end coverage silently disappears is worse than one with none.

The repository and token are created through Forgejo's API with the same shape
``app-spark-api`` uses in production (private, auto-initialised, branch-protected, and a token
scoped to that one repository), because the parts of the component this file exists to test --
authentication, transport, and the server's refusal to accept a non-fast-forward push -- are
exactly the parts a local bare repository cannot reproduce.
"""

from __future__ import annotations

import os
import secrets
import shutil
import subprocess
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest

from app_spark_agent.git import GitIdentity, GitRunner, GitWorkspace, RemoteConfig

FORGEJO_DIR = Path(__file__).resolve().parents[3] / "repo-server" / "forgejo"
BRANCH = "main"
IDENTITY = GitIdentity(name="App-Spark", email="app-spark@localhost.invalid")


@dataclass(frozen=True)
class ForgejoInstance:
    """Where the live Forgejo is and how to administer it."""

    base_url: str
    org: str
    account: str
    password: str

    def client(self) -> httpx.Client:
        """An API client authenticated as the service account."""
        return httpx.Client(
            base_url=self.base_url.rstrip("/") + "/",
            auth=(self.account, self.password),
            headers={"Accept": "application/json"},
            timeout=30.0,
        )


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key] = value
    return values


@pytest.fixture(scope="session")
def forgejo() -> ForgejoInstance:
    """Ensure a Forgejo is reachable and return how to talk to it."""
    if shutil.which("git") is None:
        pytest.fail("git must be installed to run the live Git tests")

    url = os.environ.get("APP_SPARK_FORGEJO_BASE_URL", "").strip()
    password = os.environ.get("APP_SPARK_FORGEJO_SERVICE_ACCOUNT_PASSWORD", "").strip()
    if url and password:
        return ForgejoInstance(
            base_url=url,
            org=os.environ.get("APP_SPARK_FORGEJO_ORG", "app-spark"),
            account=os.environ.get("APP_SPARK_FORGEJO_SERVICE_ACCOUNT", "app-spark-bot"),
            password=password,
        )

    just = shutil.which("just")
    if just is None:
        pytest.fail("`just` is required to start repo-server/forgejo")
    started = subprocess.run([just, "test-up"], cwd=FORGEJO_DIR, text=True, capture_output=True, check=False)
    if started.returncode != 0:
        pytest.fail(f"just test-up failed in {FORGEJO_DIR}:\n{started.stderr or started.stdout}")

    credentials_path = FORGEJO_DIR / "secrets" / "test" / "credentials.env"
    if not credentials_path.is_file():
        pytest.fail(f"Forgejo test credentials missing: {credentials_path}")
    credentials = _parse_env_file(credentials_path)
    return ForgejoInstance(
        base_url=f"http://127.0.0.1:{os.environ.get('TEST_HTTP_PORT', '3001')}",
        org=credentials.get("ORG_NAME", "app-spark"),
        account=credentials.get("SERVICE_ACCOUNT_USERNAME", "app-spark-bot"),
        password=credentials["SERVICE_ACCOUNT_PASSWORD"],
    )


@pytest.fixture
def project_remote(forgejo: ForgejoInstance) -> Iterator[RemoteConfig]:
    """Provision one private repository plus a token scoped to it, and clean both up after."""
    name = f"agent-live-{secrets.token_hex(4)}"
    token_name = f"{name}-write"
    with forgejo.client() as api:
        created = api.post(
            f"api/v1/orgs/{forgejo.org}/repos",
            json={"name": name, "private": True, "auto_init": True, "default_branch": BRANCH},
        )
        assert created.status_code == 201, created.text
        assert created.json()["private"] is True, "App-Spark repositories must be private"

        protection = api.post(
            f"api/v1/repos/{forgejo.org}/{name}/branch_protections",
            json={
                "rule_name": BRANCH,
                "enable_push": True,
                "enable_force_push": False,
                "enable_force_push_allowlist": False,
            },
        )
        assert protection.status_code in {200, 201}, protection.text

        issued = api.post(
            f"api/v1/users/{forgejo.account}/tokens",
            json={
                "name": token_name,
                "scopes": ["write:repository"],
                "repositories": [{"owner": forgejo.org, "name": name}],
            },
        )
        assert issued.status_code == 201, issued.text
        token = issued.json()

        yield RemoteConfig(
            url=f"{forgejo.base_url.rstrip('/')}/{forgejo.org}/{name}.git",
            branch=BRANCH,
            username=forgejo.account,
            token=token["sha1"],
        )

        api.delete(f"api/v1/users/{forgejo.account}/tokens/{token['id']}")
        api.delete(f"api/v1/repos/{forgejo.org}/{name}")


def open_workspace(path: Path, remote: RemoteConfig) -> GitWorkspace:
    """Build a workspace on ``path`` pointed at ``remote``, creating the directory."""
    path.mkdir(parents=True, exist_ok=True)
    return GitWorkspace(
        path=path,
        runner=GitRunner(workspace=path, identity=IDENTITY, remote=remote, timeout_seconds=60.0),
    )
