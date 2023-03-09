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
from unittest import mock

import pytest

from paas_wl.resources.kube_res.exceptions import AppEntityNotFound
from paas_wl.workloads.processes.controllers import env_is_running, get_processes_status
from paas_wl.workloads.processes.models import Instance, Process
from tests.paas_wl.cnative.specs.utils import create_cnative_deploy
from tests.paas_wl.utils.wl_app import create_wl_app
from tests.paas_wl.workloads.conftest import create_release

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestController:
    def test_get_processes_status(self, wl_app, wl_release):
        with mock.patch(
            'paas_wl.workloads.processes.readers.ProcessReader.get_by_type',
            new=lambda _self, app, process_type: Process.from_release(process_type, wl_release),
        ), mock.patch(
            'paas_wl.workloads.processes.readers.InstanceReader.list_by_process_type',
            new=lambda _self, app, process_type: [Instance(process_type=process_type, app=wl_app, name=process_type)],
        ):
            web_proc = Process.from_release('web', wl_release)
            web_proc.instances = [Instance(process_type='web', app=wl_app, name='web')]
            worker_proc = Process.from_release('worker', wl_release)
            worker_proc.instances = [Instance(process_type='worker', app=wl_app, name='worker')]
            assert get_processes_status(wl_app) == [web_proc, worker_proc]

    def test_get_processes_status_without_release(self):
        """没有发布过的 WlApp，无法获取进程信息"""
        not_release_wl_app = create_wl_app()
        assert len(get_processes_status(not_release_wl_app)) == 0

    def test_get_processes_status_with_app_entity_not_found(self, wl_app, wl_release):
        """任意进程获取状态失败，应该跳过，不影响获取其他进程状态"""

        def fake_list_by_process_type(_self, app, process_type):
            """测试用函数，若进程类型不是 web，抛出异常"""
            if process_type != 'web':
                raise AppEntityNotFound

            return [Instance(process_type=process_type, app=wl_app, name=process_type)]

        with mock.patch(
            'paas_wl.workloads.processes.readers.ProcessReader.get_by_type',
            new=lambda _self, app, process_type: Process.from_release(process_type, wl_release),
        ), mock.patch(
            'paas_wl.workloads.processes.readers.InstanceReader.list_by_process_type',
            new=fake_list_by_process_type,
        ):
            web_proc = Process.from_release('web', wl_release)
            web_proc.instances = [Instance(process_type='web', app=wl_app, name='web')]
            assert get_processes_status(wl_app) == [web_proc]

    def test_default_app_env_is_running(self, bk_app, bk_stag_env, bk_user, with_wl_apps):
        assert env_is_running(bk_stag_env) is False
        # Create a failed release at first, it should not affect the result
        create_release(bk_stag_env, bk_user, failed=True)
        assert env_is_running(bk_stag_env) is False

        create_release(bk_stag_env, bk_user, failed=False)
        assert env_is_running(bk_stag_env) is True

    def test_cnative_app_env_is_running(self, bk_cnative_app, bk_stag_env, bk_user):
        assert env_is_running(bk_stag_env) is False

        create_cnative_deploy(bk_stag_env, bk_user)
        assert env_is_running(bk_stag_env) is True
