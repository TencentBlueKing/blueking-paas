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

from paas_wl.cluster.utils import get_cluster_by_app
from paas_wl.networking.ingress.constants import AppDomainSource
from paas_wl.networking.ingress.entities.ingress import ingress_kmodel
from paas_wl.networking.ingress.managers.misc import AppDefaultIngresses, LegacyAppIngressMgr
from paas_wl.networking.ingress.models import AppDomain

pytestmark = [pytest.mark.django_db]


class TestLegacyAppIngressMgr:
    def test_list_desired_domains(self, app):
        ingress_mgr = LegacyAppIngressMgr(app)
        domains = ingress_mgr.list_desired_domains()
        cluster = get_cluster_by_app(app)
        assert len(domains) == 1
        assert (
            domains[0].host == cluster.ingress_config.default_ingress_domain_tmpl % app.scheduler_safe_name_with_region
        )


@pytest.mark.auto_create_ns
class TestAppDefaultIngresses:
    def test_integrated(self, bk_stag_engine_app):
        app_default_ingresses = AppDefaultIngresses(bk_stag_engine_app)
        app_default_ingresses.sync_ignore_empty(default_service_name='foo')
        assert len(ingress_kmodel.list_by_app(bk_stag_engine_app)) == 1

        AppDomain.objects.create(app=bk_stag_engine_app, region=bk_stag_engine_app.region, host='bar-2.com', source=AppDomainSource.AUTO_GEN)

        app_default_ingresses.sync_ignore_empty(default_service_name='foo')
        assert len(ingress_kmodel.list_by_app(bk_stag_engine_app)) == 2

        ret = app_default_ingresses.safe_update_target(service_name='foo-copy', service_port_name='foo-port-copy')
        assert ret.num_of_successful > 0
        for ingress in ingress_kmodel.list_by_app(bk_stag_engine_app):
            assert ingress.service_name == 'foo-copy'
            assert ingress.service_port_name == 'foo-port-copy'

        app_default_ingresses.delete_if_service_matches(service_name='not-matched')
        assert len(ingress_kmodel.list_by_app(bk_stag_engine_app)) == 2

        app_default_ingresses.delete_if_service_matches(service_name='foo-copy')
        assert len(ingress_kmodel.list_by_app(bk_stag_engine_app)) == 0
