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
from django_dynamic_fixture import G

from paas_wl.workloads.networking.ingress.domains.exceptions import ReplaceAppDomainFailed
from paas_wl.workloads.networking.ingress.domains.independent import ReplaceAppDomainService
from paas_wl.workloads.networking.ingress.kres_entities.ingress import ingress_kmodel
from paas_wl.workloads.networking.ingress.managers.domain import CustomDomainIngressMgr
from paas_wl.workloads.networking.ingress.models import Domain

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestReplaceAppDomainService:
    def test_invalid_input(self, bk_app, bk_stag_env, bk_stag_wl_app):
        with pytest.raises(ReplaceAppDomainFailed):
            ReplaceAppDomainService(bk_stag_env, 'invalid-name.example.com', '/')

    @pytest.mark.mock_get_structured_app
    @pytest.mark.auto_create_ns
    @pytest.mark.parametrize(
        'old_host,old_path_prefix,new_host,new_path_prefix',
        [
            # From direct to subpath
            ('foo.example.com', '/', 'bar.example.com', '/bar/'),
            # From subpath to subpath
            ('foo.example.com', '/foo/', 'bar.example.com', '/bar/'),
        ],
    )
    def test_integrated(
        self, bk_app, bk_stag_env, bk_stag_wl_app, old_host, old_path_prefix, new_host, new_path_prefix
    ):
        domain = G(
            Domain,
            name=old_host,
            path_prefix=old_path_prefix,
            module_id=bk_stag_env.module_id,
            environment_id=bk_stag_env.id,
        )
        mgr = CustomDomainIngressMgr(domain)
        mgr.sync(default_service_name=bk_stag_wl_app.name)

        # Check ingress resource beforehand
        ings = ingress_kmodel.list_by_app(bk_stag_wl_app)
        assert ings[0].domains[0].host == old_host

        ReplaceAppDomainService(bk_stag_env, old_host, old_path_prefix).replace_with(new_host, new_path_prefix, False)

        # Validate replacement
        ings = ingress_kmodel.list_by_app(bk_stag_wl_app)
        assert len(ings) == 1
        assert len(ings[0].domains) == 1
        assert ings[0].domains[0].host == new_host
        assert ings[0].domains[0].path_prefix_list == [new_path_prefix]
        assert Domain.objects.filter(
            name=new_host, path_prefix=new_path_prefix, module_id=bk_stag_env.module_id, environment_id=bk_stag_env.id
        ).exists()
