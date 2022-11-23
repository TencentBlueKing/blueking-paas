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
from pathlib import Path
from unittest import mock

import pytest
from django.utils.crypto import get_random_string

from paas_wl.platform.applications.models.build import BuildProcess
from paas_wl.platform.applications.models.config import Config
from paas_wl.release_controller.builder.tasks import start_build_process


@pytest.fixture
def engine_app(fake_app):
    Config.objects.create(
        app=fake_app, metadata={"environment": 'prod', "paas_app_code": 'foo', "module_name": 'default'}
    )
    return fake_app


@pytest.fixture
def package_path():
    return Path('./tests/assets/dj_with_hello_world_demo.tar.gz')


@pytest.fixture
def code_branch():
    return "branch"


@pytest.fixture
def code_revision():
    return "1"


@pytest.fixture
def source_code_tarball_path(engine_app, code_branch, code_revision):
    return f"'{engine_app.region}/home/{engine_app.name}:{code_branch}:{code_revision}/tar'"


@pytest.fixture
def create_build_process(api_client, engine_app, source_code_tarball_path, code_branch):
    data = {
        'procfile': {
            'web': 'gunicorn wsgi -b :$PORT --access-logfile - --error-logfile - --access-logformat \'[%(h)s] %({'
            'request_id}i)s %(u)s %(t)s "%(r)s" %(s)s %(D)s %(b)s "%(f)s" "%(a)s"\' '
        },
        'source_tar_path': source_code_tarball_path,
        'stream_channel_id': '46e0aff6-4c7f-4e83-9094-761dc86b10c1',
        'branch': code_branch,
        'extra_envs': {
            'BKPAAS_WEIXIN_REMOTE_STATIC_URL': 'https://blueking-fake.com',
            'BKPAAS_SUB_PATH': '/{region}-{name}/'.format(region=engine_app.region, name=engine_app.name),
            'BKPAAS_ENVIRONMENT': 'stag',
            'BKPAAS_REMOTE_STATIC_URL': 'http://blueking-fake.com',
            'BKPAAS_WEIXIN_URL': 'https://blueking-fake.com',
            'BKPAAS_URL': 'http://blueking-fake.com',
        },
        'revision': '28',
    }
    build_processes_url = '/regions/{region}/apps/{name}/build_processes/'.format(
        region=engine_app.region, name=engine_app.name
    )

    def handler():
        with mock.patch.object(start_build_process, 'delay', mock.Mock(return_value=None)):
            response = api_client.post(build_processes_url, data=data)
            start_build_process_args = start_build_process.delay.call_args
        return response, start_build_process_args

    return handler


@pytest.fixture
def mock_bp_executor():
    with mock.patch("paas_wl.resources.base.kres.KNamespace.wait_for_default_sa"), mock.patch(
        "paas_wl.resources.base.kres.KPod.wait_for_status"
    ), mock.patch("paas_wl.resources.base.client.K8sScheduler.get_build_log"), mock.patch(
        "paas_wl.resources.base.client.K8sScheduler.wait_build_succeeded"
    ):
        yield


@pytest.fixture
def build(mock_bp_executor, create_build_process):
    response, start_build_process_args = create_build_process()
    start_build_process(*start_build_process_args[0], **start_build_process_args[1])
    bp_uuid = response.json()["uuid"]
    bp = BuildProcess.objects.get(uuid=bp_uuid)
    return bp.build


@pytest.fixture
def scale_url(engine_app):
    return f"/regions/{engine_app.region}/apps/{engine_app.name}/processes/"


@pytest.fixture
def release_url(engine_app):
    return f'/regions/{engine_app.region}/apps/{engine_app.name}/releases/'


@pytest.fixture
def webconsole_url(engine_app):
    return (
        f'/regions/{engine_app.region}/apps/{engine_app.name}/processes/'
        f'{get_random_string(8).lower()}/instances/{get_random_string(8).lower()}/webconsole/'
    )


@pytest.fixture
def create_release(engine_app, build, api_client, release_url):
    def handler():
        data = {
            'build': build.uuid,
            'extra_envs': {
                'BKPAAS_WEIXIN_REMOTE_STATIC_URL': 'https://blueking-fake.com',
                'BKPAAS_SUB_PATH': '/{region}-{name}/'.format(region=engine_app.region, name=engine_app.name),
                'BKPAAS_ENVIRONMENT': 'stag',
                'BKPAAS_REMOTE_STATIC_URL': 'http://blueking-fake.com',
                'BKPAAS_WEIXIN_URL': 'https://blueking-fake.com',
                'BKPAAS_URL': 'http://blueking-fake.com',
            },
            'procfile': {},
        }
        response = api_client.post(release_url, data=data)
        return response

    return handler


@pytest.fixture
def mock_judge_operation_frequent():
    with mock.patch("paas_wl.workloads.processes.views_enduser.judge_operation_frequent"):
        yield
