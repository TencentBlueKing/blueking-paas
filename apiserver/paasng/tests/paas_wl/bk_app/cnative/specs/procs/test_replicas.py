# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
import pytest

from paas_wl.bk_app.cnative.specs.models import create_app_resource, generate_bkapp_name
from paas_wl.bk_app.cnative.specs.procs.exceptions import ProcNotDeployed, ProcNotFoundInRes
from paas_wl.bk_app.cnative.specs.procs.replicas import ProcReplicas
from paas_wl.bk_app.cnative.specs.resource import deploy

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture
def deploy_stag_env(bk_stag_env, bk_stag_wl_app, mock_knamespace):
    """Deploy a default payload to cluster for stag environment"""
    resource = create_app_resource(generate_bkapp_name(bk_stag_env), 'nginx:latest')
    deploy(bk_stag_env, resource.to_deployable())
    yield


@pytest.mark.skip_when_no_crds
class TestProcReplicas:
    def test_not_deployed(self, bk_stag_env, bk_stag_wl_app):
        with pytest.raises(ProcNotDeployed):
            ProcReplicas(bk_stag_env).scale('web', 1)

    def test_proc_not_found(self, bk_stag_env, deploy_stag_env):
        with pytest.raises(ProcNotFoundInRes):
            ProcReplicas(bk_stag_env).scale('invalid-name', 1)

    def test_get(self, bk_stag_env, deploy_stag_env):
        assert ProcReplicas(bk_stag_env).get('web') == 1

    def test_get_with_overlay_integrated(self, bk_stag_env, deploy_stag_env):
        assert ProcReplicas(bk_stag_env).get_with_overlay('web') == (1, False)
        ProcReplicas(bk_stag_env).scale('web', 2)
        assert ProcReplicas(bk_stag_env).get_with_overlay('web') == (2, True)
