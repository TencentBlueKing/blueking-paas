# -*- coding: utf-8 -*-
import pytest

from paas_wl.workloads.processes.models import ProcessSpec, ProcessSpecManager

pytestmark = pytest.mark.django_db


class TestProcessSpecManager:
    """Mixin class for testing process managers"""

    def test_sync(self, fake_app):
        mgr = ProcessSpecManager(fake_app)
        mgr.sync([{"name": "web", "command": "foo", "replicas": 2}, {"name": "celery", "command": "foo"}])

        assert ProcessSpec.objects.get(engine_app=fake_app, name="web").target_replicas == 2
        assert ProcessSpec.objects.get(engine_app=fake_app, name="celery").target_replicas == 1

        mgr.sync([{"name": "web", "command": "foo", "replicas": 3, "plan": "4C1G5R"}])
        web = ProcessSpec.objects.get(engine_app=fake_app, name="web")
        assert web.target_replicas == 3
        assert web.plan.name == "4C1G5R"
        assert ProcessSpec.objects.filter(engine_app=fake_app).count() == 1

        mgr.sync([{"name": "web", "command": "foo", "replicas": None, "plan": None}])
        web = ProcessSpec.objects.get(engine_app=fake_app, name="web")
        assert web.target_replicas == 3
        assert web.plan.name == "4C1G5R"
        assert ProcessSpec.objects.filter(engine_app=fake_app).count() == 1
