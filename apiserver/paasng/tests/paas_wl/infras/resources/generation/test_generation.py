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

from paas_wl.bk_app.processes.managers import AppProcessManager
from paas_wl.infras.resources.generation.version import get_mapper_version, get_proc_deployment_name
from paas_wl.utils.command import get_command_name
from tests.paas_wl.utils.wl_app import create_wl_release

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestGeneration:
    @pytest.fixture()
    def release(self, wl_app):
        return create_wl_release(
            wl_app=wl_app,
            release_params={
                "version": 2,
                "procfile": {"web": "gunicorn wsgi -w 4 -b :$PORT --access-logfile - --error-logfile"},
            },
        )

    @pytest.fixture()
    def process(self, wl_app, release):
        return AppProcessManager(app=wl_app).assemble_process(process_type="web", release=release)

    @pytest.fixture()
    def v1_mapper(self):
        return get_mapper_version("v1")

    @pytest.fixture()
    def v2_mapper(self):
        return get_mapper_version("v2")

    def test_v1_pod_name(self, v1_mapper, process):
        assert (
            v1_mapper.proc_resources(process=process).pod_name
            == f"{process.app.region}-{process.app.scheduler_safe_name}-"
            f"{process.type}-{get_command_name(process.runtime.proc_command)}-deployment"
        )

        assert (
            v1_mapper.proc_resources(process=process).deployment_name
            == f"{process.app.region}-{process.app.scheduler_safe_name}-"
            f"{process.type}-{get_command_name(process.runtime.proc_command)}-deployment"
        )

    def test_preset_process_client(self, wl_app, process, v1_mapper):
        assert (
            v1_mapper.proc_resources(process=process).pod_name
            == f"{process.app.region}-{process.app.scheduler_safe_name}-"
            f"{process.type}-{get_command_name(process.runtime.proc_command)}-deployment"
        )

    def test_v2_name(self, process, v2_mapper):
        assert (
            v2_mapper.proc_resources(process=process).pod_name
            == f"{process.app.name.replace('_', '0us0')}--{process.type}"
        )
        assert (
            v2_mapper.proc_resources(process=process).deployment_name
            == f"{process.app.name.replace('_', '0us0')}--{process.type}"
        )


def test_get_proc_deployment_name(wl_app):
    assert get_proc_deployment_name(wl_app, "web") != ""
