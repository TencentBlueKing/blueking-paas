# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
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

import uuid
from typing import Iterator
from unittest import mock

import pytest

from paas_wl.bk_app.agent_sandbox.kres_entities import AgentSandbox, AgentSandboxKresApp
from paasng.platform.agent_sandbox.sandbox import KubernetesPodSandbox

from .stubs import DEFAULT_WORKDIR, StubDaemonClient, StubDaemonClientFactory


@pytest.fixture(scope="session", autouse=True)
def _skip_if_old_k8s_version(skip_if_old_k8s_version):
    """Auto-apply shared k8s version skip guard for agent_sandbox tests."""


@pytest.fixture()
def stub_daemon_factory() -> StubDaemonClientFactory:
    """Fixture that provides a StubDaemonClientFactory instance.

    :returns: A factory for creating stub daemon clients with shared state.
    """
    return StubDaemonClientFactory()


@pytest.fixture()
def stub_daemon_client(stub_daemon_factory: StubDaemonClientFactory) -> StubDaemonClient:
    """Fixture that provides a StubDaemonClient instance.

    :returns: A stub daemon client for testing sandbox operations.
    """
    return stub_daemon_factory.get_client()


@pytest.fixture()
def stub_kres_app(bk_app) -> AgentSandboxKresApp:
    """Fixture that provides an AgentSandboxKresApp instance for testing.

    :param bk_app: The application fixture.
    :returns: An AgentSandboxKresApp instance.
    """
    return AgentSandboxKresApp(
        paas_app_id=bk_app.code,
        tenant_id=bk_app.tenant_id,
        target="default",
    )


@pytest.fixture()
def stub_agent_sandbox(stub_kres_app: AgentSandboxKresApp) -> AgentSandbox:
    """Fixture that provides an AgentSandbox entity for testing.

    :param stub_kres_app: The kres app fixture.
    :returns: An AgentSandbox entity.
    """
    sandbox_id = uuid.uuid4().hex
    return AgentSandbox.create(
        app=stub_kres_app,
        name=f"test-sbx-{sandbox_id[:8]}",
        sandbox_id=sandbox_id,
        workdir=DEFAULT_WORKDIR,
        snapshot="python:3.11-alpine",
        env={"TEST_VAR": "test_value"},
    )


@pytest.fixture()
def stub_k8s_sandbox(
    stub_agent_sandbox: AgentSandbox,
    stub_daemon_factory: StubDaemonClientFactory,
) -> Iterator[KubernetesPodSandbox]:
    """Fixture that provides a KubernetesPodSandbox with StubDaemonClient backend.

    This fixture creates a KubernetesPodSandbox that uses StubDaemonClient
    for all daemon operations, enabling unit testing without real K8s/daemon.

    :param stub_agent_sandbox: The agent sandbox entity fixture.
    :param stub_daemon_factory: The daemon client factory fixture.
    :returns: A KubernetesPodSandbox instance with stub backend.
    """
    sandbox = KubernetesPodSandbox(
        entity=stub_agent_sandbox,
        router_endpoint="agent-sbx-router.example.com",
        daemon_token="test-token",
    )

    # Patch the daemon_client method to return stub client
    def patched_daemon_client():
        return stub_daemon_factory.get_client()

    with mock.patch.object(sandbox, "daemon_client", patched_daemon_client):
        yield sandbox
