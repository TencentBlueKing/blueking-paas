"""Render the chart to verify what each runtime provider accepts: replicas, context storage, config."""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from dynaconf.vendor.ruamel.yaml import YAML

HELM = shutil.which("helm")
CHART = Path(__file__).resolve().parents[1] / "charts" / "app-spark-api"
pytestmark = pytest.mark.skipif(HELM is None, reason="Helm is required for chart rendering tests")

E2B_CONFIG = {
    "api_key": "e2b-key",
    "api_url": "https://bkapi.example.com/api/agent_sandbox/prod/e2b",
    "callback_base_url": "https://app-spark-api.example.com/api-svc",
    "template": "app-spark-agent",
}
BK_REPO_CONTEXTS = {"backend": "bk_repo", "root": "app-spark-contexts"}


def run_helm_template(overrides: dict[str, Any]) -> subprocess.CompletedProcess[str]:
    command = [HELM or "helm", "template", "spark-test", str(CHART)]
    for key, value in overrides.items():
        command.extend(["--set-json", f"{key}={json.dumps(value)}"])
    return subprocess.run(command, check=False, capture_output=True, text=True)


def render_deployment(overrides: dict[str, Any]) -> dict[str, Any]:
    rendered = run_helm_template(overrides)
    assert rendered.returncode == 0, rendered.stderr
    resources = [resource for resource in YAML(typ="safe").load_all(rendered.stdout) if resource]
    (deployment,) = [resource for resource in resources if resource["kind"] == "Deployment"]
    return deployment


def collect_render_error(overrides: dict[str, Any]) -> str:
    rendered = run_helm_template(overrides)
    assert rendered.returncode != 0, "the chart rendered although it should have refused"
    return rendered.stderr


def make_e2b_overrides(replicas: int, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build values for an e2b release; extra overrides win, and a None value unsets that key."""
    return {
        "replicaCount": replicas,
        "agent.runtimeProvider": "e2b",
        "agent.runtimeProviderConfig": E2B_CONFIG,
        **(extra or {}),
    }


def test_e2b_runs_several_replicas_on_shared_context_storage():
    deployment = render_deployment(make_e2b_overrides(2, {"agent.contextStorage": BK_REPO_CONTEXTS}))

    assert deployment["spec"]["replicas"] == 2


@pytest.mark.parametrize(
    ("context_storage", "named_backend"),
    [
        pytest.param(
            {"backend": "host_tmp_path", "root": "/data/app-spark/agent-contexts"}, "host_tmp_path", id="host"
        ),
        # Anything but bk_repo is refused, so a misspelling cannot slip through to the first cold start.
        pytest.param({"backend": "bkrepo", "root": "app-spark-contexts"}, "bkrepo", id="misspelled"),
        # No backend: the application refuses such a config, and it shares nothing either way.
        pytest.param({"backend": None, "root": "/data/app-spark/agent-contexts"}, "host_tmp_path", id="no-backend"),
        # No contextStorage at all: the application falls back to host_tmp_path.
        pytest.param(None, "host_tmp_path", id="no-context-storage"),
    ],
)
def test_several_replicas_need_bk_repo_context_storage(context_storage, named_backend):
    error = collect_render_error(make_e2b_overrides(2, {"agent.contextStorage": context_storage}))

    assert "replicaCount=2" in error
    assert "agent.contextStorage.backend=bk_repo" in error
    assert f'got "{named_backend}"' in error


def test_one_e2b_replica_keeps_per_pod_context_storage():
    deployment = render_deployment(make_e2b_overrides(1))

    assert deployment["spec"]["replicas"] == 1


@pytest.mark.parametrize("replicas", [1, 2])
def test_bk_repo_does_not_take_the_merged_host_path_for_its_repository(replicas):
    """Switching only the backend keeps the default host path as root, which bk_repo would read as a repository."""
    error = collect_render_error(make_e2b_overrides(replicas, {"agent.contextStorage.backend": "bk_repo"}))

    assert "agent.contextStorage.root" in error
    assert "/data/app-spark/agent-contexts" in error


@pytest.mark.parametrize("field", list(E2B_CONFIG))
def test_e2b_refuses_to_render_without_a_required_field(field):
    """Missing, the API would fail only at the first conversation: the TCP probes cannot tell."""
    config = {**E2B_CONFIG, field: ""}

    error = collect_render_error(make_e2b_overrides(1, {"agent.runtimeProviderConfig": config}))

    assert f"agent.runtimeProviderConfig.{field} is required" in error


@pytest.mark.parametrize(
    ("overrides", "strategy"),
    [
        # An API process that exits leaves its sandboxes running, so old and new Pods may overlap.
        pytest.param(make_e2b_overrides(1), "RollingUpdate", id="e2b"),
        # Two local_process Pods would work on the same workspaces and Runtime state at once.
        pytest.param({}, "Recreate", id="local-process"),
    ],
)
def test_the_update_strategy_follows_the_runtime_provider(overrides, strategy):
    assert render_deployment(overrides)["spec"]["strategy"]["type"] == strategy


@pytest.mark.parametrize("provider", [None, "local_process"])
def test_local_process_still_requires_one_replica(provider):
    overrides: dict[str, Any] = {"replicaCount": 2, "agent.contextStorage": BK_REPO_CONTEXTS}
    if provider is not None:
        overrides["agent.runtimeProvider"] = provider

    assert "local_process runtime requires replicaCount=1" in collect_render_error(overrides)


def test_no_replica_is_refused():
    assert "at least 1" in collect_render_error({"replicaCount": 0})
