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

from paas_wl.platform.applications.models import WlApp
from paas_wl.platform.applications.models.managers.app_res_ver import AppResVerManager
from paas_wl.resources.kube_res.base import ResourceField, ResourceList
from paas_wl.workloads.processes.controllers import env_is_running, list_processes
from paas_wl.workloads.processes.entities import Instance, Process, Runtime, Schedule
from tests.paas_wl.cnative.specs.utils import create_cnative_deploy
from tests.paas_wl.workloads.conftest import create_release

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


def make_process(wl_app: WlApp, process_type: str) -> Process:
    process = Process(
        app=wl_app,
        name="should-set-by-mapper",
        version=1,
        replicas=1,
        type=process_type,
        schedule=Schedule(cluster_name="", tolerations=[], node_selector={}),
        runtime=Runtime(
            envs={},
            image=process_type,
            command=[],
            args=[],
        ),
    )
    process.name = AppResVerManager(wl_app).curr_version.deployment(process).name
    return process


@pytest.fixture
def mock_reader():
    class setter:
        def __init__(self, list_processes, list_instances):
            self.list_processes = list_processes
            self.list_instances = list_instances

        def set_processes(self, processes):
            self.list_processes.return_value = ResourceList(
                items=processes, metadata=ResourceField({"resourceVersion": "1"})
            )

        def set_instances(self, instances):
            self.list_instances.return_value = ResourceList(
                items=instances, metadata=ResourceField({"resourceVersion": "1"})
            )

    with mock.patch(
        "paas_wl.workloads.processes.readers.ProcessReader.list_by_app_with_meta"
    ) as list_processes, mock.patch(
        "paas_wl.workloads.processes.readers.InstanceReader.list_by_app_with_meta"
    ) as list_instances:
        yield setter(list_processes, list_instances)


def test_list_processes(bk_stag_env, wl_app, wl_release, mock_reader):
    mock_reader.set_processes([make_process(wl_app, "web"), make_process(wl_app, "worker")])
    mock_reader.set_instances(
        [
            Instance(app=wl_app, name="web", process_type="web"),
            Instance(app=wl_app, name="worker", process_type="worker"),
        ]
    )

    web_proc = make_process(wl_app, "web")
    web_proc.instances = [Instance(process_type='web', app=wl_app, name='web')]
    worker_proc = make_process(wl_app, "worker")
    worker_proc.instances = [Instance(process_type='worker', app=wl_app, name='worker')]
    assert list_processes(bk_stag_env).processes == [web_proc, worker_proc]


def test_list_processes_boundary_case(bk_stag_env, wl_app, wl_release, mock_reader):
    mock_reader.set_processes(
        # worker 没有实例, 不会被忽略
        # beat 未定义在 Procfile, 会被忽略
        [
            make_process(wl_app, "web"),
            make_process(wl_app, "worker"),
            make_process(wl_app, "beat"),
        ]
    )
    mock_reader.set_instances([Instance(app=wl_app, name="web", process_type="web")])

    web_proc = make_process(wl_app, "web")
    web_proc.instances = [Instance(process_type='web', app=wl_app, name='web')]
    worker_proc = make_process(wl_app, "worker")
    assert list_processes(bk_stag_env).processes == [web_proc, worker_proc]


def test_list_processes_without_release(bk_stag_env, wl_app, wl_release, mock_reader):
    """没有发布过的 WlApp，无法获取进程信息"""
    mock_reader.set_processes([make_process(wl_app, "web")])
    mock_reader.set_instances([Instance(app=wl_app, name="web", process_type="web")])
    wl_release.delete()
    assert len(list_processes(bk_stag_env).processes) == 0


class TestController:
    def test_default_app_env_is_running(self, bk_app, bk_stag_env, bk_user, with_wl_apps):
        assert env_is_running(bk_stag_env) is False
        # Create a failed release at first, it should not affect the result
        create_release(bk_stag_env, bk_user, failed=True)
        assert env_is_running(bk_stag_env) is False

        create_release(bk_stag_env, bk_user, failed=False)
        assert env_is_running(bk_stag_env) is True

        # Simulate case when stag environment was offline
        bk_stag_env.is_offlined = True
        bk_stag_env.save()
        assert env_is_running(bk_stag_env) is False

    def test_cnative_app_env_is_running(self, bk_cnative_app, bk_stag_env, bk_user):
        assert env_is_running(bk_stag_env) is False

        create_cnative_deploy(bk_stag_env, bk_user)
        assert env_is_running(bk_stag_env) is True

        # Simulate case when stag environment was offline
        bk_stag_env.is_offlined = True
        bk_stag_env.save()
        assert env_is_running(bk_stag_env) is False
