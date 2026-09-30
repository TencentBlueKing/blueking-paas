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
Agent wheel there as a wheel. The provider then starts it exactly as it starts the Agent a
production template ships.

### 作为当 Agent E2B template 不可用时的妥协方案

以上说明仅针对当前阶段，基于不包含 Agent 应用程序的默认 e2b template 跑通集成测试的场景，后续如果
E2B 已经提供了包含 Agent 程序的 template，则不再需要这一套基于 whl 上传的流程。当然，目前的流程也
可以被保留下来，用于相关 template 不可用时的补充。
"""

from __future__ import annotations

import gzip
import logging
import shutil
import subprocess
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import attrs
import pytest

from app_spark_api.agent.runtime.entities import DirectModelAccess, E2BConfig, structure_e2b_config
from app_spark_api.agent.runtime.exceptions import AgentConfigurationError
from app_spark_api.agent.runtime.providers.e2b import E2BProvider

if TYPE_CHECKING:
    from e2b import AsyncSandbox

    from app_spark_api.agent.runtime.entities import AgentRuntimeHandle, ModelAccess

AGENT_PROJECT_DIR = Path(__file__).resolve().parents[4] / "agent"
SANDBOX_VENV = "/tmp/app-spark-agent-venv"
SANDBOX_WORKSPACE = "/tmp/app-spark-workspace"
SANDBOX_STATE_DIR = "/tmp/app-spark-state"
SANDBOX_LOG = "/tmp/app-spark-agent.log"
LIVE_E2B_TIMEOUT_SECONDS = 300

# The live suites do not verify replication out of the sandbox, which cannot reach a test server
# on this machine anyway. A callback address configured in the settings still wins.
UNREACHABLE_CALLBACK_BASE_URL = "http://127.0.0.1:9"

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
    :return: Valid E2B connection settings with a short test sandbox lifetime, pointed at the
        Agent that :class:`BootstrappedE2BProvider` installs.
    """
    if settings.AGENT_RUNTIME_PROVIDER != "e2b":
        pytest.skip("AGENT_RUNTIME_PROVIDER is not e2b")
    raw_config = {"callback_base_url": UNREACHABLE_CALLBACK_BASE_URL, **settings.AGENT_RUNTIME_PROVIDER_CONFIG}
    try:
        config = structure_e2b_config(raw_config)
    except AgentConfigurationError:
        pytest.skip("A valid E2B provider configuration is required")
    return attrs.evolve(
        config,
        # Fixtures normally kill their sandboxes; this bounds leaked resources if a test worker
        # dies. A test lasts a few minutes, and every turn renews it, so nothing idles out mid-test.
        idle_timeout_seconds=LIVE_E2B_TIMEOUT_SECONDS,
        agent_command=f"{SANDBOX_VENV}/bin/python -m app_spark_agent",
        workspace_dir=SANDBOX_WORKSPACE,
        state_dir=SANDBOX_STATE_DIR,
        agent_log_path=SANDBOX_LOG,
    )


async def resolve_fake_model_access() -> ModelAccess:
    """The deterministic fake model, which needs no credential and makes no network call."""
    return DirectModelAccess(model="fake:write-file")


class BootstrappedE2BProvider(E2BProvider):
    """The production provider, with the Agent installed into the default template first.

    :param config: Settings from :func:`require_e2b_config`.
    :param bundle: Artifacts from :func:`build_agent_bundle`.
    """

    def __init__(self, config: E2BConfig, bundle: AgentBundle) -> None:
        super().__init__(config)
        self.bundle = bundle

    async def ensure(self, *, model_access: Any = resolve_fake_model_access, **kwargs: Any) -> AgentRuntimeHandle:  # type: ignore[override]
        """Provision as in production; callers that pass no model access get the fake model."""
        return await super().ensure(model_access=model_access, **kwargs)

    async def _prepare_sandbox(self, sandbox: AsyncSandbox) -> None:
        logger.info("Installing the test Agent into sandbox %s", sandbox.sandbox_id)
        await install_agent_bundle(sandbox, self.bundle)


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


def _run_local(*command: str) -> None:
    """Run one local build step and retain its output if it fails."""
    subprocess.run(command, check=True, capture_output=True, text=True, timeout=180)
