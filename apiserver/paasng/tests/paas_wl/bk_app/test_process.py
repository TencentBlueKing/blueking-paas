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
from django.conf import settings

from paas_wl.bk_app.processes.managers import AppProcessManager
from paas_wl.utils.command import get_command_name
from tests.paas_wl.utils.wl_app import create_wl_app, create_wl_release

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestProcess:
    @pytest.fixture(autouse=True)
    def _setup(self):
        self.app = create_wl_app()
        self.release = create_wl_release(
            wl_app=self.app,
            release_params={
                "version": 2,
                "procfile": {"web": "gunicorn wsgi -w 4 -b :$PORT --access-logfile - --error-logfile"},
            },
        )

    def test_command_name_normal(self):
        sample_process = AppProcessManager(app=self.app).assemble_process(process_type="web", release=self.release)
        assert get_command_name(sample_process.runtime.proc_command) == "gunicorn"

        self.release.procfile = {"web": "command -x -z -y"}
        sample_process = AppProcessManager(app=self.app).assemble_process(process_type="web", release=self.release)
        assert get_command_name(sample_process.runtime.proc_command) == "command"

    def test_command_name_celery(self):
        self.release.procfile = {"web": "python manage.py celery"}
        sample_process = AppProcessManager(app=self.app).assemble_process(process_type="web", release=self.release)
        assert get_command_name(sample_process.runtime.proc_command) == "celery"

    def test_commnad_name_with_slash(self):
        self.release.procfile = {"web": "/bin/test/fake"}
        sample_process = AppProcessManager(app=self.app).assemble_process(process_type="web", release=self.release)
        assert get_command_name(sample_process.runtime.proc_command) == "fake"

        self.release.procfile = {"web": "/bin/test/fake -g -s"}
        sample_process = AppProcessManager(app=self.app).assemble_process(process_type="web", release=self.release)
        assert get_command_name(sample_process.runtime.proc_command) == "fake"


class TestProcessManager:
    @pytest.fixture(autouse=True)
    def _setup(self):
        self.app = create_wl_app(
            force_app_info={
                "region": settings.DEFAULT_REGION_NAME,
                "name": "bkapp-lala_la-stag",
                "structure": {"web": 1, "worker1": 1, "worker2": 1},
            }
        )

    def test_assemble_process(self):
        release = create_wl_release(
            wl_app=self.app,
            release_params={
                "version": 2,
                "procfile": {"web": "gunicorn wsgi -w 4 -b :$PORT --access-logfile - --error-logfile"},
            },
        )
        sample_process = AppProcessManager(app=self.app).assemble_process(process_type="web", release=release)

        assert sample_process.runtime.proc_command == "gunicorn wsgi -w 4 -b :$PORT --access-logfile - --error-logfile"
        assert get_command_name(sample_process.runtime.proc_command) == "gunicorn"
        assert sample_process.version == 2
        assert sample_process.type == "web"
        assert sample_process.app.namespace == "bkapp-lala0us0la-stag"
        assert sample_process.app.name == "bkapp-lala_la-stag"
        assert sample_process.app.region == settings.DEFAULT_REGION_NAME

    def test_assemble_processes(self):
        release = create_wl_release(
            wl_app=self.app,
            release_params={
                "version": 2,
                "procfile": {
                    "web": "gunicorn wsgi -w 4 -b :$PORT --access-logfile - --error-logfile",
                    "worker1": "gunicorn wsgi -w 4 -b :$PORT --access-logfile - --error-logfile",
                    "worker2": "gunicorn wsgi -w 4 -b :$PORT --access-logfile - --error-logfile",
                },
            },
        )
        sample_processes = list(AppProcessManager(app=self.app).assemble_processes(release=release))
        assert len(sample_processes) == 3
