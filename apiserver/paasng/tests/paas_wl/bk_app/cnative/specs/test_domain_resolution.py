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

from paas_wl.bk_app.cnative.specs.crd.bk_app import HostAlias
from paas_wl.bk_app.cnative.specs.domain_res import inject_to_app_resource
from paas_wl.bk_app.cnative.specs.models import DomainResolution as DomainResolutionModel
from paas_wl.bk_app.cnative.specs.models import create_app_resource

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture
def bk_app_resource(bk_app, bk_stag_env, bk_user):
    return create_app_resource(bk_app.name, 'nginx:latest')


@pytest.fixture
def domain_resolution(bk_app):
    """创建一个 DomainResolution 对象"""
    domain_resolution = DomainResolutionModel.objects.create(
        application_id=bk_app.id,
        nameservers=['192.168.1.1', '192.168.1.2'],
        host_aliases=[
            {
                'ip': 'bk_app_code_test',
                'hostnames': [
                    'bk_app_code_test',
                    'bk_app_code_test_x',
                ],
            }
        ],
    )
    return domain_resolution


def test_inject_to_app_resource(bk_stag_env, bk_app_resource, domain_resolution):
    inject_to_app_resource(bk_stag_env, bk_app_resource)

    assert bk_app_resource.spec.domainResolution
    assert bk_app_resource.spec.domainResolution.nameservers == ['192.168.1.1', '192.168.1.2']
    assert bk_app_resource.spec.domainResolution.hostAliases == [
        HostAlias(
            ip='bk_app_code_test',
            hostnames=[
                'bk_app_code_test',
                'bk_app_code_test_x',
            ],
        )
    ]
