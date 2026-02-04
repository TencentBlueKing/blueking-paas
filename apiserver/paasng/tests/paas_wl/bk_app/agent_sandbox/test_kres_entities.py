import pytest

from paas_wl.bk_app.agent_sandbox.kres_entities import AgentSandbox, AgentSandboxKresApp, agent_sandbox_kmodel
from paasng.core.tenant.user import DEFAULT_TENANT_ID

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


def test_create_and_get(namespace_maker):
    """Create a sandbox and get it back to test the kmodel functionality."""
    sbx_app = AgentSandboxKresApp(
        paas_app_id="demo-sbx",
        tenant_id=DEFAULT_TENANT_ID,
    )
    namespace_maker.make(sbx_app.namespace)
    sbx = AgentSandbox.create(
        sbx_app,
        sandbox_id="abc123",
        workdir="/app",
        image="python:3.11-alpine",
    )
    agent_sandbox_kmodel.create(sbx)

    # Get the sandbox back and compare fields
    created_sbx = agent_sandbox_kmodel.get(sbx_app, sbx.name)
    assert created_sbx.name == sbx.name
    assert created_sbx.sandbox_id == sbx.sandbox_id
    assert created_sbx.workdir == sbx.workdir
    assert created_sbx.image == sbx.image
