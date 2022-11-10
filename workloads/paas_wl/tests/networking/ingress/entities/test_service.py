# -*- coding: utf-8 -*-
import pytest

from paas_wl.networking.ingress.entities.service import ProcessService, PServicePortPair, service_kmodel
from paas_wl.resources.kube_res.exceptions import AppEntityNotFound
from tests.utils.app import release_setup

pytestmark = pytest.mark.django_db


class TestProcessService:
    @pytest.fixture(autouse=True)
    def _setup_data(self, app):
        release_setup(
            fake_app=app,
            build_params={"procfile": {"web": "python manage.py runserver", "worker": "python manage.py celery"}},
            release_params={"version": 5},
        )

    @pytest.mark.auto_create_ns
    def test_integrated(self, app):
        items = service_kmodel.list_by_app(app)
        assert len(items) == 0

        service = ProcessService(
            app=app,
            name='foo-service',
            process_type='web',
            ports=[PServicePortPair(name='http', port=80, target_port=80)],
        )
        service_kmodel.save(service)

        items = service_kmodel.list_by_app(app)
        assert len(items) == 1

        for item in items:
            service_kmodel.delete(item)

        items = service_kmodel.list_by_app(app)
        assert len(items) == 0

    def test_get_not_found(self, app):
        with pytest.raises(AppEntityNotFound):
            service_kmodel.get(app, 'non-existed-service')

    @pytest.mark.auto_create_ns
    def test_get_normal(self, app):
        service = ProcessService(
            app=app,
            name='foo-service',
            process_type='web',
            ports=[PServicePortPair(name='http', port=80, target_port=80)],
        )
        service_kmodel.save(service)

        obj = service_kmodel.get(app, 'foo-service')
        assert obj is not None

    def test_update_not_found(self, app):
        service = ProcessService(
            app=app,
            name='non-existed-service',
            process_type='web',
            ports=[PServicePortPair(name='http', port=80, target_port=80)],
        )
        with pytest.raises(AppEntityNotFound):
            service_kmodel.update(service, update_method='patch')

    @pytest.mark.auto_create_ns
    def test_update(self, app):
        service = ProcessService(
            app=app,
            name='foo-service',
            process_type='web',
            ports=[PServicePortPair(name='http', port=80, target_port=80)],
        )
        service_kmodel.save(service)
        service.ports[0].target_port = 8080
        service_kmodel.update(service)

        service_new = service_kmodel.get(app, service.name)
        assert service_new.ports[0].target_port == 8080

    @pytest.mark.auto_create_ns
    def test_update_with_less_ports(self, app):
        service = ProcessService(
            app=app,
            name='foo-service',
            process_type='web',
            ports=[
                PServicePortPair(name='http', port=80, target_port=80),
                PServicePortPair(name='https', port=83, target_port=8080),
            ],
        )
        service_kmodel.save(service)
        service.ports = service.ports[1:]
        service_kmodel.update(service)

        service_new = service_kmodel.get(app, service.name)
        assert len(service_new.ports) == 1
