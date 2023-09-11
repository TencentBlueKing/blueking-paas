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

from paas_wl.deploy.app_res.generation import get_mapper_version
from paas_wl.resources.base.exceptions import ResourceMissing
from paas_wl.resources.utils.basic import get_client_by_app
from paas_wl.workloads.processes.managers import AppProcessManager
from paas_wl.workloads.processes.utils import get_command_name
from tests.paas_wl.utils.wl_app import create_wl_release

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestGeneration:
    @pytest.fixture
    def release(self, wl_app):
        return create_wl_release(
            wl_app=wl_app,
            build_params={"procfile": {"web": "gunicorn wsgi -w 4 -b :$PORT --access-logfile - --error-logfile"}},
            release_params={"version": 2},
        )

    @pytest.fixture
    def process(self, wl_app, release):
        return AppProcessManager(app=wl_app).assemble_process(process_type="web", release=release)

    @pytest.fixture
    def client(self, wl_app):
        return get_client_by_app(wl_app)

    @pytest.fixture
    def v1_mapper(self):
        return get_mapper_version("v1")

    @pytest.fixture
    def v2_mapper(self):
        return get_mapper_version("v2")

    def test_v1_pod_name(self, v1_mapper, process):
        assert (
            v1_mapper.pod(process=process).name == f"{process.app.region}-{process.app.scheduler_safe_name}-"
            f"{process.type}-{get_command_name(process.runtime.proc_command)}-deployment"
        )

        assert (
            v1_mapper.deployment(process=process).name == f"{process.app.region}-{process.app.scheduler_safe_name}-"
            f"{process.type}-{get_command_name(process.runtime.proc_command)}-deployment"
        )

    def test_preset_process_client(self, wl_app, process, client, v1_mapper):
        assert (
            v1_mapper.pod(process=process, client=client).name
            == f"{process.app.region}-{process.app.scheduler_safe_name}-"
            f"{process.type}-{get_command_name(process.runtime.proc_command)}-deployment"
        )

    def test_v1_get(self, wl_app, process, client, v1_mapper):
        with pytest.raises(ValueError):
            v1_mapper.pod(process=process).get()

        mapper = v1_mapper.pod(process=process, client=client)
        with pytest.raises(ResourceMissing):
            mapper.get()

        kp = Mock(return_value={"items": [1, 2, 3]})
        with patch('paas_wl.resources.base.kres.NameBasedOperations.get', kp):
            assert mapper.get() == {"items": [1, 2, 3]}

    def test_v1_delete(self, wl_app, process, client, v1_mapper):
        kd = Mock(return_value=None)
        with patch('paas_wl.resources.base.kres.NameBasedOperations.delete', kd):
            mapper = v1_mapper.pod(process=process, client=client)
            assert mapper.delete() is None
            args, kwargs = kd.call_args_list[0]
            assert kd.called
            assert kwargs['name'] == mapper.name
            assert kwargs['namespace'] == mapper.namespace

    def test_v1_create(self, wl_app, process, client, v1_mapper):
        kd = Mock(return_value={"items": [1, 2, 3]})
        with patch('paas_wl.resources.base.kres.NameBasedOperations.create', kd):
            mapper = v1_mapper.pod(process=process, client=client)
            assert mapper.create(body={}) == {"items": [1, 2, 3]}
            args, kwargs = kd.call_args_list[0]
            assert kd.called
            assert kwargs['name'] == mapper.name
            assert kwargs['namespace'] == mapper.namespace

    def test_v2_name(self, process, v2_mapper):
        assert v2_mapper.pod(process=process).name == f"{process.app.name.replace('_', '0us0')}--{process.type}"
        assert v2_mapper.deployment(process=process).name == f"{process.app.name.replace('_', '0us0')}--{process.type}"
