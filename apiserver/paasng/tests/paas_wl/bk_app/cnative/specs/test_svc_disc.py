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

from paas_wl.bk_app.cnative.specs.crd.bk_app import SvcDiscEntryBkSaaS
from paas_wl.bk_app.cnative.specs.models import SvcDiscConfig as SvcDiscConfigModel
from paas_wl.bk_app.cnative.specs.models import create_app_resource
from paas_wl.bk_app.cnative.specs.svc_disc import ConfigMapManager, SvcDiscConfigManager, inject_to_app_resource
from paas_wl.infras.resources.base.kres import KNamespace
from paas_wl.infras.resources.utils.basic import get_client_by_app

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestSvcDiscConfig:
    @pytest.fixture
    def bk_app_resource(self, bk_app, bk_stag_env, bk_user):
        return create_app_resource(bk_app.name, 'nginx:latest')

    @pytest.fixture
    def create_namespace(self, bk_stag_env, with_wl_apps):
        wl_app = bk_stag_env.wl_app
        with get_client_by_app(wl_app) as client:
            body = {
                'metadata': {'name': wl_app.namespace},
            }
            KNamespace(client).create_or_update(
                bk_stag_env.wl_app.namespace,
                body=body,
                update_method='patch',
            )
            yield
            KNamespace(client).delete(bk_stag_env.wl_app.namespace)

    @pytest.fixture
    def svc_disc(self, bk_app):
        """创建一个 SvcDiscConfig 对象"""
        svc_disc = SvcDiscConfigModel.objects.create(
            application_id=bk_app.id,
            bk_saas=[
                {
                    'bkAppCode': 'bk_app_code_test',
                    'moduleName': 'module_name_test',
                }
            ],
        )
        return svc_disc

    def test_normal(self, bk_app, bk_stag_env, bk_stag_wl_app, bk_app_resource, create_namespace, svc_disc):
        SvcDiscConfigManager(env=bk_stag_env, bk_app_name=bk_app_resource.metadata.name).sync()

        mgr = ConfigMapManager(bk_stag_env, bk_app_name=bk_app.name)
        assert mgr.read_data()[mgr.key_bk_saas] != ''

    def test_deletion(self, bk_app, bk_stag_env, bk_stag_wl_app, bk_app_resource, create_namespace, svc_disc):
        SvcDiscConfigManager(env=bk_stag_env, bk_app_name=bk_app_resource.metadata.name).sync()
        mgr = ConfigMapManager(bk_stag_env, bk_app_name=bk_app.name)
        assert mgr.exists()

        svc_disc = SvcDiscConfigModel.objects.get(application_id=bk_app.id)
        svc_disc.bk_saas = []
        svc_disc.save()
        svc_disc.refresh_from_db()

        # Remove the service discovery config and apply again
        SvcDiscConfigManager(env=bk_stag_env, bk_app_name=bk_app_resource.metadata.name).sync()
        mgr = ConfigMapManager(bk_stag_env, bk_app_name=bk_app.name)
        assert not mgr.exists()

    def test_inject_to_app_resource(self, bk_stag_env, bk_app_resource, svc_disc):
        inject_to_app_resource(bk_stag_env, bk_app_resource)

        assert bk_app_resource.spec.svcDiscovery
        assert bk_app_resource.spec.svcDiscovery.bkSaaS == [
            SvcDiscEntryBkSaaS(
                bkAppCode='bk_app_code_test',
                moduleName='module_name_test',
            )
        ]
