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

import pytest

from paas_wl.bk_app.agent_sandbox import constants as sbx_constants
from paasng.platform.agent_sandbox.sandbox import AgentSandboxFactory

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture()
def sandbox(bk_app):
    factory = AgentSandboxFactory(bk_app, sbx_constants.DEFAULT_TARGET)
    id_ = uuid.uuid4().hex
    sandbox = factory.create(name=f"test-sbx-{id_}", sandbox_id=id_, snapshot=sbx_constants.DEFAULT_SNAPSHOT)
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
