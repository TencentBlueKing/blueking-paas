# -*- coding: utf-8 -*-
import pytest
from django.conf import settings

from paas_wl.workloads.processes.managers import AppProcessManager
from paas_wl.workloads.processes.utils import get_command_name
from tests.utils.app import random_fake_app, release_setup

pytestmark = pytest.mark.django_db


class TestProcess:
    @pytest.fixture(autouse=True)
    def setUp(self):
        self.app = random_fake_app()
        self.release = release_setup(
            fake_app=self.app,
            build_params={"procfile": {"web": "gunicorn wsgi -w 4 -b :$PORT --access-logfile - --error-logfile"}},
            release_params={"version": 2},
        )

    def test_command_name_normal(self):
        sample_process = AppProcessManager(app=self.app).assemble_process(process_type="web", release=self.release)
        assert get_command_name(sample_process.runtime.proc_command) == "gunicorn"

        self.release.build.procfile = {"web": "command -x -z -y"}
        sample_process = AppProcessManager(app=self.app).assemble_process(process_type="web", release=self.release)
        assert get_command_name(sample_process.runtime.proc_command) == "command"

    def test_command_name_celery(self):
        self.release.build.procfile = {"web": "python manage.py celery"}
        sample_process = AppProcessManager(app=self.app).assemble_process(process_type="web", release=self.release)
        assert get_command_name(sample_process.runtime.proc_command) == "celery"

    def test_commnad_name_with_slash(self):
        self.release.build.procfile = {"web": "/bin/test/fake"}
        sample_process = AppProcessManager(app=self.app).assemble_process(process_type="web", release=self.release)
        assert get_command_name(sample_process.runtime.proc_command) == "fake"

        self.release.build.procfile = {"web": "/bin/test/fake -g -s"}
        sample_process = AppProcessManager(app=self.app).assemble_process(process_type="web", release=self.release)
        assert get_command_name(sample_process.runtime.proc_command) == "fake"


class TestProcessManager:
    @pytest.fixture(autouse=True)
    def setUp(self):
        self.app = random_fake_app(
            force_app_info={
                "region": settings.FOR_TESTS_DEFAULT_REGION,
                "name": "bkapp-lala_la-stag",
                "structure": {"web": 1, "worker1": 1, "worker2": 1},
            }
        )

    def test_assemble_process(self):
        release = release_setup(
            fake_app=self.app,
            build_params={"procfile": {"web": "gunicorn wsgi -w 4 -b :$PORT --access-logfile - --error-logfile"}},
            release_params={"version": 2},
        )
        sample_process = AppProcessManager(app=self.app).assemble_process(process_type="web", release=release)

        assert sample_process.runtime.proc_command == "gunicorn wsgi -w 4 -b :$PORT --access-logfile - --error-logfile"
        assert get_command_name(sample_process.runtime.proc_command) == "gunicorn"
        assert sample_process.version == 2
        assert sample_process.type == "web"
        assert sample_process.app.namespace == "bkapp-lala0us0la-stag"
        assert sample_process.app.name == "bkapp-lala_la-stag"
        assert sample_process.app.region == settings.FOR_TESTS_DEFAULT_REGION

    def test_assemble_processes(self):
        release = release_setup(
            fake_app=self.app,
            build_params={
                "procfile": {
                    "web": "gunicorn wsgi -w 4 -b :$PORT --access-logfile - --error-logfile",
                    "worker1": "gunicorn wsgi -w 4 -b :$PORT --access-logfile - --error-logfile",
                    "worker2": "gunicorn wsgi -w 4 -b :$PORT --access-logfile - --error-logfile",
                }
            },
            release_params={"version": 2},
        )
        sample_processes = list(AppProcessManager(app=self.app).assemble_processes(release=release))
        assert len(sample_processes) == 3
