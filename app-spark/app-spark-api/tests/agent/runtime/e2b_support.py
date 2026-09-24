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

"""Build and install a real Agent Runtime in an otherwise empty E2B sandbox.

The default template has Python 3.12 and no Agent. Build the Agent wheel locally, stage its
locked runtime dependencies locally, and transfer those artifacts plus uv into the sandbox.
This keeps the live test independent of the sandbox's pip index while still installing the
Agent wheel there as a wheel.

### 作为当 Agent E2B template 不可用时的妥协方案

以上说明仅针对当前阶段，基于不包含 Agent 应用程序的默认 e2b template 跑通集成测试的场景，后续如果
E2B 已经提供了包含 Agent 程序的 template，则不再需要这一套基于 whl 上传的流程。当然，目前的流程也
可以被保留下来，用于相关 template 不可用时的补充。
"""

from __future__ import annotations

import asyncio
import gzip
import logging
import shutil
import subprocess
import tarfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import attrs
import pytest

from app_spark_api.agent.runtime.entities import E2BConfig, structure_e2b_config
from app_spark_api.agent.runtime.exceptions import AgentConfigurationError, AgentUnavailableError

if TYPE_CHECKING:
    from e2b import AsyncSandbox

    from app_spark_api.agent.runtime.client import AgentRuntimeClient
    from app_spark_api.agent.runtime.entities import AgentRuntimeHandle, RuntimeHealth

AGENT_PROJECT_DIR = Path(__file__).resolve().parents[4] / "agent"
SANDBOX_VENV = "/tmp/app-spark-agent-venv"
SANDBOX_WORKSPACE = "/tmp/app-spark-workspace"
SANDBOX_STATE_DIR = "/tmp/app-spark-state"
SANDBOX_LOG = "/tmp/app-spark-agent.log"
HEALTH_TIMEOUT_SECONDS = 20
LIVE_E2B_TIMEOUT_SECONDS = 300

logger = logging.getLogger("tests.e2b")


@dataclass(frozen=True)
class AgentBundle:
    """Local artifacts transferred into the E2B sandbox."""

    wheel: Path
    dependencies: Path
    uv_archive: Path


def require_e2b_config(settings: Any) -> E2BConfig:
    """Skip a live test unless the API service has a usable E2B configuration.

    :param settings: Django settings object supplied by pytest-django.
    :return: Valid E2B connection settings with a short test sandbox lifetime.
    """
    if settings.AGENT_RUNTIME_PROVIDER != "e2b":
        pytest.skip("AGENT_RUNTIME_PROVIDER is not e2b")
    try:
        config = structure_e2b_config(settings.AGENT_RUNTIME_PROVIDER_CONFIG)
    except AgentConfigurationError:
        pytest.skip("A valid E2B provider configuration is required")
    # Fixtures normally kill their sandboxes; this bounds leaked resources if a test worker dies.
    return attrs.evolve(config, timeout_seconds=LIVE_E2B_TIMEOUT_SECONDS)


def build_agent_bundle(build_dir: Path) -> AgentBundle:
    """Build the Agent wheel and a portable archive of its locked runtime dependencies.

    :param build_dir: Temporary directory for build artifacts.
    :return: The three files the sandbox installer uploads.
    """
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("uv is required to build the Agent test bundle")

    logger.info("Building Agent wheel and staging locked runtime dependencies")
    wheel_dir = build_dir / "wheels"
    _run_local(uv, "build", "--wheel", "--out-dir", str(wheel_dir), str(AGENT_PROJECT_DIR))
    (wheel,) = wheel_dir.glob("app_spark_agent-*.whl")

    requirements = build_dir / "requirements.txt"
    _run_local(
        uv,
        "export",
        "--project",
        str(AGENT_PROJECT_DIR),
        "--no-dev",
        "--no-emit-project",
        "--no-hashes",
        "--output-file",
        str(requirements),
    )
    staging_venv = build_dir / "staging-venv"
    _run_local(uv, "venv", "--python", "3.14", str(staging_venv))
    _run_local(uv, "pip", "install", "--python", str(staging_venv / "bin/python"), "-r", str(requirements))

    dependencies = build_dir / "dependencies.tar.gz"
    with tarfile.open(dependencies, "w:gz") as archive:
        archive.add(staging_venv / "lib/python3.14/site-packages", arcname=".")

    uv_archive = build_dir / "uv.gz"
    with Path(uv).open("rb") as source, gzip.open(uv_archive, "wb") as target:
        shutil.copyfileobj(source, target)
    logger.info(
        "Bundle ready: wheel %.1f MiB, dependencies %.1f MiB, uv %.1f MiB",
        wheel.stat().st_size / 1024**2,
        dependencies.stat().st_size / 1024**2,
        uv_archive.stat().st_size / 1024**2,
    )
    return AgentBundle(wheel=wheel, dependencies=dependencies, uv_archive=uv_archive)


async def install_agent_bundle(sandbox: AsyncSandbox, bundle: AgentBundle) -> None:
    """Upload a wheel and its prerequisites, then install the wheel inside the sandbox.

    :param sandbox: Newly created E2B sandbox.
    :param bundle: Artifacts prepared by :func:`build_agent_bundle`.
    """
    for source, destination in (
        (bundle.uv_archive, "/tmp/uv.gz"),
        (bundle.dependencies, "/tmp/agent-dependencies.tar.gz"),
        (bundle.wheel, f"/tmp/{bundle.wheel.name}"),
    ):
        logger.info("Uploading %s (%.1f MiB)", source.name, source.stat().st_size / 1024**2)
        with source.open("rb") as content:
            await sandbox.files.write(destination, content, request_timeout=120)

    for label, command in (
        ("Preparing uv", "gzip -d /tmp/uv.gz && chmod +x /tmp/uv"),
        ("Installing Python 3.14", "/tmp/uv python install 3.14"),
        ("Creating Agent virtualenv", f"/tmp/uv venv --python 3.14 {SANDBOX_VENV}"),
        (
            "Unpacking Agent dependencies",
            f"tar -xzf /tmp/agent-dependencies.tar.gz -C {SANDBOX_VENV}/lib/python3.14/site-packages",
        ),
        (
            "Installing Agent wheel offline",
            f"/tmp/uv pip install --offline --no-deps --python {SANDBOX_VENV}/bin/python /tmp/{bundle.wheel.name}",
        ),
        ("Preparing workspace", f"mkdir -p {SANDBOX_WORKSPACE} {SANDBOX_STATE_DIR}"),
    ):
        logger.info("%s in sandbox %s", label, sandbox.sandbox_id)
        await sandbox.commands.run(command, timeout=150, request_timeout=180)
    logger.info("Agent bundle installed in sandbox %s", sandbox.sandbox_id)


async def start_agent(
    sandbox: AsyncSandbox, handle: AgentRuntimeHandle, *, port: int, app_port: int, project_id: str
) -> None:
    """Start the installed Agent with its fake model and the provider's Bearer token.

    :param sandbox: Sandbox holding the installed Agent.
    :param handle: Provider handle whose token the Agent must accept.
    :param port: Port exposed by the provider.
    :param app_port: Fixed sandbox port reserved for application preview.
    :param project_id: Project identity for the Agent configuration.
    """
    envs = {
        "APP_SPARK_AGENT_WORKSPACE": SANDBOX_WORKSPACE,
        "APP_SPARK_AGENT_STATE_DIR": SANDBOX_STATE_DIR,
        "APP_SPARK_AGENT_RUNTIME_TOKEN": handle.runtime_token,
        "APP_SPARK_AGENT_MODEL": "fake:write-file",
        "APP_SPARK_AGENT_PORT": str(port),
        "APP_SPARK_AGENT_APP_PORT": str(app_port),
        "APP_SPARK_AGENT_PROJECT_ID": project_id,
        "APP_SPARK_AGENT_IDLE_TIMEOUT_SECONDS": "0",
    }
    # A log on disk makes a startup failure inspectable after the detached command exits.
    logger.info("Starting Agent in sandbox %s on port %s", sandbox.sandbox_id, port)
    await sandbox.commands.run(
        f"{SANDBOX_VENV}/bin/python -m uvicorn app_spark_agent.server.asgi:app "
        f"--host 0.0.0.0 --port {port} > {SANDBOX_LOG} 2>&1",
        background=True,
        envs=envs,
        cwd=SANDBOX_WORKSPACE,
        timeout=0,
    )


async def wait_for_health(sandbox: AsyncSandbox, client: AgentRuntimeClient, *, port: int) -> RuntimeHealth:
    """Wait until the HTTP Runtime behind the exposed E2B port answers.

    :param sandbox: Sandbox used to retrieve startup logs on failure.
    :param client: Client using the provider's handle and Bearer token.
    :param port: Agent Runtime port inside the sandbox.
    :return: First successful health snapshot.
    :raises AssertionError: If the Runtime never becomes reachable.
    """
    deadline = time.monotonic() + HEALTH_TIMEOUT_SECONDS
    last_error: AgentUnavailableError | None = None
    while time.monotonic() < deadline:
        try:
            health = await client.health()
        except AgentUnavailableError as exc:
            last_error = exc
            await asyncio.sleep(1)
        else:
            logger.info("Agent Runtime is healthy in sandbox %s", sandbox.sandbox_id)
            return health

    direct = await sandbox.commands.run(
        "curl -sS -o /dev/null -w '%{http_code}' "
        f'-H "Authorization: Bearer $APP_SPARK_AGENT_RUNTIME_TOKEN" http://127.0.0.1:{port}/health',
        envs={"APP_SPARK_AGENT_RUNTIME_TOKEN": client.handle.runtime_token},
    )
    log = await sandbox.files.read(SANDBOX_LOG)
    raise AssertionError(
        f"Agent Runtime never became healthy: {last_error}; direct status: {direct.stdout}; log tail: {str(log)[-2000:]}"
    )


def _run_local(*command: str) -> None:
    """Run one local build step and retain its output if it fails."""
    subprocess.run(command, check=True, capture_output=True, text=True, timeout=180)
