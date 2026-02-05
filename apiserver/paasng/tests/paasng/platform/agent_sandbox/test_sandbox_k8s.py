# -*- coding: utf-8 -*-
import pytest
from kubernetes.client.apis import VersionApi

from paas_wl.bk_app.agent_sandbox import constants as sbx_constants
from paas_wl.infras.resources.base.base import get_client_by_cluster_name
from paasng.platform.agent_sandbox.sandbox import AgentSandboxFactory
from tests.utils.cluster import CLUSTER_NAME_FOR_TESTING
from tests.utils.helpers import kube_ver_lt

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture(scope="session", autouse=True)
def _skip_if_old_k8s_version(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock(), get_client_by_cluster_name(CLUSTER_NAME_FOR_TESTING) as k8s_client:
        k8s_version = VersionApi(k8s_client).get_code()

    if kube_ver_lt(k8s_version, (1, 20)):
        pytest.skip("Skip tests because current k8s version less than 1.20")


@pytest.fixture()
def sandbox(bk_app):
    factory = AgentSandboxFactory(bk_app)
    sandbox = factory.create()
    yield sandbox

    factory.destroy(sandbox)


class TestKubernetesPodSandbox:
    def test_exec_simple(self, sandbox):
        result = sandbox.exec("pwd")
        assert result.exit_code == 0
        assert result.stdout.strip() == sbx_constants.DEFAULT_WORKDIR

    def test_exec_with_env(self, sandbox):
        result = sandbox.exec("echo $FOO", env={"FOO": "BAR"})
        assert result.exit_code == 0
        assert result.stdout.strip() == "BAR"

    def test_run_code(self, sandbox):
        code_result = sandbox.code_run("print('hello-agent')")
        assert code_result.exit_code == 0
        assert "hello-agent" in code_result.stdout

    def test_create_folder(self, sandbox):
        sandbox.create_folder(f"{sbx_constants.DEFAULT_WORKDIR}/data", mode="755")
        assert sandbox.exec("test -d /workspace/data").exit_code == 0

    def test_single_file_simple_operations(self, sandbox):
        payload = b"hello\x00world\n"
        remote_path = f"{sbx_constants.DEFAULT_WORKDIR}/blob.bin"
        sandbox.upload_file(payload, remote_path)
        downloaded = sandbox.download_file(remote_path)
        assert downloaded == payload

        sandbox.delete_file(remote_path)
        assert sandbox.exec(f"test -e {remote_path}").exit_code != 0
