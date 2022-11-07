# -*- coding: utf-8 -*-
from unittest.mock import Mock, patch

import pytest

from paas_wl.networking.ingress.entities.ingress import PIngressDomain, ProcessIngress
from paas_wl.networking.ingress.utils import (
    get_main_process_service_name,
    get_service_dns_name,
    guess_default_service_name,
)
from paas_wl.resources.kube_res.exceptions import AppEntityNotFound

pytestmark = [pytest.mark.django_db]


class TestGuessDefaultServiceName:
    def test_structure_with_web(self, fake_app, set_structure):
        set_structure(fake_app, {"web": 1})
        assert guess_default_service_name(fake_app) == f'{fake_app.region}-{fake_app.name}-web'

    def test_structure_without_web(self, fake_app, set_structure):
        set_structure(fake_app, {"worker": 1})
        assert guess_default_service_name(fake_app) == f'{fake_app.region}-{fake_app.name}-worker'

    def test_empty_structure(self, fake_app):
        assert guess_default_service_name(fake_app) == f'{fake_app.region}-{fake_app.name}-web'


class TestGetMainProcessServiceName:
    def test_normal(self, app):
        patch_mgr = Mock(
            return_value=[
                ProcessIngress(
                    app=app,
                    name="",
                    domains=[PIngressDomain(host="bar.com")],
                    service_name=app.name,
                    service_port_name="http",
                )
            ]
        )
        with patch('paas_wl.networking.ingress.entities.service.AppEntityManager.list_by_app', patch_mgr):
            assert get_main_process_service_name(app) == app.name
            assert patch_mgr.called

    def test_none(self, app):
        patch_mgr = Mock(return_value=[])
        with patch('paas_wl.networking.ingress.entities.service.AppEntityManager.list_by_app', patch_mgr):
            with pytest.raises(AppEntityNotFound):
                assert not get_main_process_service_name(app)
                assert not patch_mgr.called


def test_get_service_dns_name(app):
    name = get_service_dns_name(app, 'web')
    _, ns = name.split('.')
    assert ns == app.namespace
