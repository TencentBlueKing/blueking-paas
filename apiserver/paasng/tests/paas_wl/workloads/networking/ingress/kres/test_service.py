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

import pytest

from paas_wl.infras.resources.kube_res.exceptions import AppEntityNotFound
from paas_wl.workloads.networking.ingress.entities import PServicePortPair
from paas_wl.workloads.networking.ingress.kres_entities.service import ProcessService, service_kmodel
from tests.paas_wl.utils.wl_app import create_wl_release

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestProcessService:
    @pytest.fixture(autouse=True)
    def _setup_data(self, bk_stag_wl_app):
        create_wl_release(
            wl_app=bk_stag_wl_app,
            release_params={
                "version": 5,
                "procfile": {"web": "python manage.py runserver", "worker": "python manage.py celery"},
            },
        )

    @pytest.mark.auto_create_ns
    def test_integrated(self, bk_stag_wl_app):
        items = service_kmodel.list_by_app(bk_stag_wl_app)
        assert len(items) == 0

        service = ProcessService(
            app=bk_stag_wl_app,
            name="foo-service",
            process_type="web",
            ports=[PServicePortPair(name="http", port=80, target_port=80)],
        )
        service_kmodel.save(service)

        items = service_kmodel.list_by_app(bk_stag_wl_app)
        assert len(items) == 1

        for item in items:
            service_kmodel.delete(item)

        items = service_kmodel.list_by_app(bk_stag_wl_app)
        assert len(items) == 0

    def test_get_not_found(self, bk_stag_wl_app):
        with pytest.raises(AppEntityNotFound):
            service_kmodel.get(bk_stag_wl_app, "non-existed-service")

    @pytest.mark.auto_create_ns
    def test_get_normal(self, bk_stag_wl_app):
        service = ProcessService(
            app=bk_stag_wl_app,
            name="foo-service",
            process_type="web",
            ports=[PServicePortPair(name="http", port=80, target_port=80)],
        )
        service_kmodel.save(service)

        obj = service_kmodel.get(bk_stag_wl_app, "foo-service")
        assert obj is not None

    def test_update_not_found(self, bk_stag_wl_app):
        service = ProcessService(
            app=bk_stag_wl_app,
            name="non-existed-service",
            process_type="web",
            ports=[PServicePortPair(name="http", port=80, target_port=80)],
        )
        with pytest.raises(AppEntityNotFound):
            service_kmodel.update(service, update_method="patch")

    @pytest.mark.auto_create_ns
    def test_update(self, bk_stag_wl_app):
        service = ProcessService(
            app=bk_stag_wl_app,
            name="foo-service",
            process_type="web",
            ports=[PServicePortPair(name="http", port=80, target_port=80)],
        )
        service_kmodel.save(service)
        service.ports[0].target_port = 8080
        service_kmodel.update(service)

        service_new = service_kmodel.get(bk_stag_wl_app, service.name)
        assert service_new.ports[0].target_port == 8080

    @pytest.mark.auto_create_ns
    def test_update_with_less_ports(self, bk_stag_wl_app):
        service = ProcessService(
            app=bk_stag_wl_app,
            name="foo-service",
            process_type="web",
            ports=[
                PServicePortPair(name="http", port=80, target_port=80),
                PServicePortPair(name="https", port=83, target_port=8080),
            ],
        )
        service_kmodel.save(service)
        service.ports = service.ports[1:]
        service_kmodel.update(service)

        service_new = service_kmodel.get(bk_stag_wl_app, service.name)
        assert len(service_new.ports) == 1
