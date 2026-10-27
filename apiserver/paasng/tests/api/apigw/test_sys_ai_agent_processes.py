# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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


import datetime
import uuid
from types import SimpleNamespace
from unittest import mock

import pytest
from bkpaas_auth.models import user_id_encoder
from django.conf import settings
from django.utils import timezone
from rest_framework import status

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.processes.controllers import ProcessesInfo
from paas_wl.bk_app.processes.entities import Runtime
from paas_wl.bk_app.processes.kres_entities import Instance, Process
from paas_wl.bk_app.processes.models import ProcessSpec, ProcessSpecPlan
from paas_wl.infras.resources.kube_res.base import Schedule
from paasng.misc.audit.models import AppOperationRecord
from paasng.platform.applications.constants import DeployPolicy
from paasng.platform.applications.models import Application
from paasng.platform.modules.models import Module

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

OPERATOR = "ut-virtual-operator"


def _list_url(app_code: str, module_name: str, env: str = "stag") -> str:
    return f"/sys/api/bkapps/applications/{app_code}/modules/{module_name}/envs/{env}/processes/list/"


def _update_url(app_code: str, module_name: str, env: str = "stag") -> str:
    return f"/sys/api/bkapps/applications/{app_code}/modules/{module_name}/envs/{env}/processes/"


@pytest.fixture()
def ai_agent_app_with_wl_apps(bk_app: Application, _with_wl_apps) -> Application:
    bk_app.is_ai_agent_app = True
    bk_app.save(update_fields=["is_ai_agent_app"])
    return bk_app


@pytest.fixture()
def module(ai_agent_app_with_wl_apps: Application) -> Module:
    return ai_agent_app_with_wl_apps.get_default_module()


@pytest.fixture()
def stag_env(module: Module):
    return module.envs.get(environment="stag")


@pytest.fixture()
def wl_processes_info(stag_env) -> ProcessesInfo:
    wl_app = stag_env.wl_app
    instance = Instance(
        app=wl_app,
        name="bkapp-foo-stag--web-699599bf76-78jzf",
        process_type="web",
        image="docker.example.com/bkpaas/docker/foo/default:1.0.0",
        start_time="2024-08-16T02:07:55Z",
        state="Running",
        rich_status="Running",
        ready=True,
        version=3,
    )
    process = Process(
        app=wl_app,
        name="bkapp-foo-stag--web",
        type="web",
        version=3,
        replicas=2,
        schedule=Schedule(cluster_name="default", tolerations=[], node_selector={}),
        runtime=Runtime(envs={}, image=instance.image, command=[], args=[], proc_command="python manage.py runserver"),
        instances=[instance],
    )
    # 构造 metadata 对象, 序列化器需要通过 metadata.name 获取进程名称 (与从集群读取时一致)
    process.fulfill_runtime(replicas=2, success=1, metadata=SimpleNamespace(name="bkapp-foo-stag--web"))
    return ProcessesInfo(processes=[process], rv_proc="100", rv_inst="200")


@pytest.fixture()
def sandbox_env(module: Module):
    """把应用切换为隔离沙箱部署模式 (由 CR 直接渲染 Pod, 无 Deployment)"""
    application = module.application
    application.deploy_policy = DeployPolicy.ISOLATED.value
    application.save(update_fields=["deploy_policy"])
    return module.envs.get(environment="stag")


@pytest.fixture()
def list_instances_only(sandbox_env):
    wl_app = sandbox_env.wl_app
    other_app = mock.MagicMock(spec=WlApp, name="ut-other-wl-app", uuid=uuid.uuid4().hex, module_name="other")

    def _build_process(app, name: str) -> Process:
        instance = Instance(
            app=app,
            name=f"{app.name}--{name}-0",
            process_type=name,
            image="docker.example.com/bkpaas/docker/foo/default:1.0.0",
            start_time="2024-08-16T02:07:55Z",
            state="Running",
            rich_status="Running",
            ready=True,
            version=3,
        )
        process = Process(
            app=app,
            name=f"{app.name}--{name}",
            type=name,
            version=3,
            replicas=1,
            schedule=Schedule(cluster_name="default", tolerations=[], node_selector={}),
            runtime=Runtime(envs={}, image=instance.image, command=[], args=[]),
            instances=[instance],
        )
        process.fulfill_runtime(replicas=1, success=1, metadata=SimpleNamespace(name=f"{app.name}--{name}"))
        return process

    with mock.patch(
        "paas_wl.bk_app.processes.views.ProcInstByEnvListWatcher.list_instances_only",
        return_value=ProcessesInfo(
            processes=[_build_process(wl_app, "web"), _build_process(other_app, "web")],
            rv_proc="300",
            rv_inst="300",
        ),
    ) as list_instances_only:
        yield list_instances_only


class TestSysListProcesses:
    """应用态查询进程接口测试"""

    @pytest.fixture()
    def list_processes(self, wl_processes_info: ProcessesInfo):
        with (
            mock.patch(
                "paas_wl.bk_app.processes.views.ProcInstByModuleEnvListWatcher.list",
                return_value=wl_processes_info,
            ) as watcher_list,
            mock.patch(
                "paas_wl.bk_app.processes.views.ProcessManager.list_processes_specs",
                return_value=[{"name": "web", "target_replicas": 1, "target_status": "start"}],
            ),
        ):
            yield watcher_list

    def test_list_success(
        self,
        sys_aidev_api_client,
        ai_agent_app_with_wl_apps: Application,
        module: Module,
        list_processes: mock.MagicMock,
    ):
        """AIDEV 可以查询 AI Agent 应用环境的进程实际状态, 返回结构与用户态接口一致"""
        resp = sys_aidev_api_client.get(_list_url(ai_agent_app_with_wl_apps.code, module.name))

        assert resp.status_code == status.HTTP_200_OK, resp.json()
        data = resp.json()
        # 结构必须与用户态接口完全一致
        assert set(data) == {"processes", "instances", "process_packages"}
        assert data["processes"]["metadata"]["resource_version"] == "100"
        assert data["instances"]["metadata"]["resource_version"] == "200"
        assert data["process_packages"] == [{"name": "web", "target_replicas": 1, "target_status": "start"}]

        # 进程 / 实例均为集群中查询到的 "实际状态"
        process = data["processes"]["items"][0]
        assert (process["type"], process["module_name"], process["replicas"], process["version"]) == (
            "web",
            module.name,
            2,
            3,
        )
        instance = data["instances"]["items"][0]
        assert instance["name"] == "bkapp-foo-stag--web-699599bf76-78jzf"
        assert (instance["process_type"], instance["state"], instance["ready"]) == ("web", "Running", True)

        list_processes.assert_called_once_with()

    def test_list_sandbox_app_instances_only(
        self,
        sys_aidev_api_client,
        ai_agent_app_with_wl_apps: Application,
        module: Module,
        sandbox_env,
        list_instances_only: mock.MagicMock,
    ):
        """隔离沙箱应用没有 Deployment, 按 Pod 构造进程状态, 且只包含路径对应应用的实例"""
        resp = sys_aidev_api_client.get(_list_url(ai_agent_app_with_wl_apps.code, module.name))

        assert resp.status_code == status.HTTP_200_OK, resp.json()
        data = resp.json()
        assert len(data["processes"]["items"]) == 1
        assert data["processes"]["items"][0]["type"] == "web"
        assert len(data["instances"]["items"]) == 1
        assert data["instances"]["items"][0]["state"] == "Running"
        assert data["processes"]["metadata"]["resource_version"] == "300"

    def test_list_basic_maintainer_denied(
        self, sys_api_client, ai_agent_app_with_wl_apps: Application, module: Module
    ):
        """BASIC_MAINTAINER 拥有部分系统 API 权限, 但不能调用仅 AIDEV 可用的接口"""
        resp = sys_api_client.get(_list_url(ai_agent_app_with_wl_apps.code, module.name))

        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.json()["code"] == "SYSAPI_CLIENT_PERM_DENIED"

    def test_non_ai_agent_app_denied(self, sys_aidev_api_client, bk_app: Application):
        """对非 AI Agent 应用调用时返回 403"""
        resp = sys_aidev_api_client.get(_list_url(bk_app.code, bk_app.get_default_module().name))

        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.json()["code"] == "AI_AGENT_APP_REQUIRED"


class TestSysUpdateProcess:
    """应用态操作进程接口测试"""

    @pytest.fixture()
    def process_spec(self, stag_env) -> ProcessSpec:
        # NOTE: 默认进程规格套餐在本测试目录的 conftest 中不存在，因此按需创建
        plan, _ = ProcessSpecPlan.objects.get_or_create(name="Starter", defaults={"max_replicas": 5})
        spec = ProcessSpec.objects.create(
            name="web",
            target_replicas=2,
            target_status="start",
            engine_app_id=stag_env.engine_app_id,
            plan=plan,
            tenant_id=stag_env.tenant_id,
        )
        # 避免频率限制干扰用例（真实场景中 ProcessSpec 早已存在，不会刚创建就被操作）
        ProcessSpec.objects.filter(pk=spec.pk).update(updated=timezone.now() - datetime.timedelta(minutes=1))
        spec.refresh_from_db()
        return spec

    @pytest.fixture()
    def proc_ctl(self):
        with mock.patch("paas_wl.bk_app.processes.views.get_proc_ctl") as get_proc_ctl:
            yield get_proc_ctl.return_value

    @pytest.fixture()
    def audit_record(self):
        with mock.patch("paas_wl.bk_app.processes.views.add_app_audit_record") as add_app_audit_record:
            yield add_app_audit_record

    @staticmethod
    def _payload(**overrides) -> dict:
        return {"operate_type": "stop", "process_type": "web", "operator": OPERATOR, **overrides}

    def test_update_success(
        self,
        sys_aidev_api_client,
        ai_agent_app_with_wl_apps: Application,
        module: Module,
        process_spec: ProcessSpec,
        proc_ctl,
        audit_record: mock.MagicMock,
    ):
        """AIDEV 可以停止 AI Agent 应用的进程, 操作人仅用于记录审计"""
        resp = sys_aidev_api_client.post(
            _update_url(ai_agent_app_with_wl_apps.code, module.name), data=self._payload()
        )

        assert resp.status_code == status.HTTP_200_OK, resp.json()
        assert resp.json() == {"target_replicas": 2, "target_status": "start"}
        proc_ctl.stop.assert_called_once_with("web")

        audit_record.assert_called_once()
        kwargs = audit_record.call_args.kwargs
        assert kwargs["user"] == user_id_encoder.encode(settings.USER_TYPE, OPERATOR)
        assert (kwargs["app_code"], kwargs["operation"], kwargs["attribute"]) == (
            ai_agent_app_with_wl_apps.code,
            "stop",
            "web",
        )

    def test_invalid_payload(
        self,
        sys_aidev_api_client,
        ai_agent_app_with_wl_apps: Application,
        module: Module,
        proc_ctl,
        audit_record: mock.MagicMock,
    ):
        """operate_type 非法时返回 400, 且不产生任何副作用"""
        payload = {"operate_type": "restart", "process_type": "web", "operator": OPERATOR}
        resp = sys_aidev_api_client.post(_update_url(ai_agent_app_with_wl_apps.code, module.name), data=payload)

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        audit_record.assert_not_called()
        proc_ctl.stop.assert_not_called()

    def test_update_basic_maintainer_denied(
        self, sys_api_client, ai_agent_app_with_wl_apps: Application, module: Module
    ):
        """BASIC_MAINTAINER 拥有部分系统 API 权限, 但不能调用仅 AIDEV 可用的接口, 且不会产生审计记录"""
        resp = sys_api_client.post(_update_url(ai_agent_app_with_wl_apps.code, module.name), data=self._payload())

        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.json()["code"] == "SYSAPI_CLIENT_PERM_DENIED"
        # 越权请求不能触发真实的进程操作
        assert not AppOperationRecord.objects.filter(operation="stop", attribute="web").exists()

    def test_non_ai_agent_app_denied(self, sys_aidev_api_client, bk_app: Application):
        """对非 AI Agent 应用调用时返回 403"""
        resp = sys_aidev_api_client.post(
            _update_url(bk_app.code, bk_app.get_default_module().name), data=self._payload()
        )

        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.json()["code"] == "AI_AGENT_APP_REQUIRED"
