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

from paas_wl.bk_app.cnative.specs.crd.bk_app import SvcDiscConfig, SvcDiscEntryBkSaaS
from paas_wl.bk_app.cnative.specs.models import create_app_resource
from paas_wl.bk_app.cnative.specs.svc_disc import ConfigMapManager, apply_configmap

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestApplyConfigmap:
    @pytest.fixture
    def res_without_svc_disc(self, bk_app, bk_stag_env, bk_user):
        """A BkAppResource without service discovery config"""
        return create_app_resource(bk_app.name, "nginx:latest")

    @pytest.fixture
    def res_with_svc_disc(self, bk_app, bk_stag_env, bk_user):
        """A BkAppResource with service discovery config"""
        resource = create_app_resource(bk_app.name, "nginx:latest")
        resource.spec.svcDiscovery = SvcDiscConfig(
            bkSaaS=[
                SvcDiscEntryBkSaaS(bkAppCode="foo"),
                SvcDiscEntryBkSaaS(bkAppCode="bar", moduleName="backend"),
            ]
        )
        return resource

    def test_normal(self, bk_app, bk_stag_env, bk_stag_wl_app, res_with_svc_disc, with_stag_ns):
        apply_configmap(bk_stag_env, res_with_svc_disc)
        mgr = ConfigMapManager(bk_stag_env, bk_app_name=bk_app.name)
        assert mgr.read_data()[mgr.key_bk_saas] != ""

    def test_deletion(
        self, bk_app, bk_stag_env, bk_stag_wl_app, res_with_svc_disc, res_without_svc_disc, with_stag_ns
    ):
        apply_configmap(bk_stag_env, res_with_svc_disc)
        mgr = ConfigMapManager(bk_stag_env, bk_app_name=bk_app.name)
        assert mgr.exists()

        # Remove the service discovery config and apply again
        apply_configmap(bk_stag_env, res_without_svc_disc)
        mgr = ConfigMapManager(bk_stag_env, bk_app_name=bk_app.name)
        assert not mgr.exists()
