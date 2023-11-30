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
from unittest.mock import Mock, patch

import pytest

from paas_wl.infras.resources.kube_res.exceptions import AppEntityNotFound
from paas_wl.workloads.networking.ingress.kres_entities.ingress import PIngressDomain, ProcessIngress
from paas_wl.workloads.networking.ingress.utils import (
    get_main_process_service_name,
    get_service_dns_name,
    guess_default_service_name,
    make_service_name,
    parse_process_type,
)

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestGuessDefaultServiceName:
    def test_structure_with_web(self, bk_stag_wl_app, set_structure):
        set_structure(bk_stag_wl_app, {"web": 1})
        assert guess_default_service_name(bk_stag_wl_app) == f"{bk_stag_wl_app.region}-{bk_stag_wl_app.name}-web"

    def test_structure_without_web(self, bk_stag_wl_app, set_structure):
        set_structure(bk_stag_wl_app, {"worker": 1})
        assert guess_default_service_name(bk_stag_wl_app) == f"{bk_stag_wl_app.region}-{bk_stag_wl_app.name}-worker"

    def test_empty_structure(self, bk_stag_wl_app):
        assert guess_default_service_name(bk_stag_wl_app) == f"{bk_stag_wl_app.region}-{bk_stag_wl_app.name}-web"


class TestGetMainProcessServiceName:
    def test_normal(self, bk_stag_wl_app):
        patch_mgr = Mock(
            return_value=[
                ProcessIngress(
                    app=bk_stag_wl_app,
                    name="",
                    domains=[PIngressDomain(host="bar.com")],
                    service_name=bk_stag_wl_app.name,
                    service_port_name="http",
                )
            ]
        )
        with patch(
            "paas_wl.workloads.networking.ingress.kres_entities.service.AppEntityManager.list_by_app", patch_mgr
        ):
            assert get_main_process_service_name(bk_stag_wl_app) == bk_stag_wl_app.name
            assert patch_mgr.called

    def test_none(self, bk_stag_wl_app):
        patch_mgr = Mock(return_value=[])
        with patch(
            "paas_wl.workloads.networking.ingress.kres_entities.service.AppEntityManager.list_by_app", patch_mgr
        ), pytest.raises(AppEntityNotFound):
            assert not get_main_process_service_name(bk_stag_wl_app)
        assert patch_mgr.called


def test_get_service_dns_name(bk_stag_wl_app):
    name = get_service_dns_name(bk_stag_wl_app, "web")
    _, ns = name.split(".")
    assert ns == bk_stag_wl_app.namespace


def test_parse_process_type(bk_stag_wl_app):
    svc_name = make_service_name(bk_stag_wl_app, "web")
    assert parse_process_type(bk_stag_wl_app, svc_name) == "web"
