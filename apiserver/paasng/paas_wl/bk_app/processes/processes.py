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

import json
from typing import Dict, List, Optional

from attrs import asdict, define, field
from django.utils.functional import cached_property
from kubernetes.client.exceptions import ApiException
from kubernetes.utils.quantity import parse_quantity
from six import ensure_text

from paas_wl.bk_app.applications.constants import WlAppType
from paas_wl.bk_app.applications.managers import get_metadata
from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.cnative.specs.constants import MODULE_NAME_ANNO_KEY
from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppResource
from paas_wl.bk_app.cnative.specs.procs.quota import ResQuotaReader
from paas_wl.bk_app.cnative.specs.procs.replicas import AutoscalingReader, ReplicasReader
from paas_wl.bk_app.cnative.specs.resource import get_mres_from_cluster, list_mres_by_env
from paas_wl.bk_app.processes.constants import DEFAULT_CNATIVE_MAX_REPLICAS, ProcessTargetStatus
from paas_wl.bk_app.processes.controllers import list_processes
from paas_wl.bk_app.processes.entities import Status
from paas_wl.bk_app.processes.exceptions import InstanceNotFound
from paas_wl.bk_app.processes.kres_entities import Process
from paas_wl.bk_app.processes.models import ProcessSpecManager
from paas_wl.bk_app.processes.readers import process_kmodel
from paas_wl.bk_app.processes.serializers import ProcessSpecSLZ
from paas_wl.infras.cluster.utils import get_cluster_by_app
from paas_wl.infras.resources.base.bcs.client import bcs_client_cls
from paas_wl.infras.resources.base.kres import KPod
from paas_wl.infras.resources.utils.basic import get_client_by_app
from paasng.platform.applications.models import Application, ModuleEnvironment
from paasng.platform.applications.tenant import get_tenant_id_for_app
from paasng.platform.engine.constants import AppEnvName
from paasng.platform.engine.models.deployment import ProcessTmpl


def condense_processes(processes: "List[Process]") -> "List[PlainProcess]":
    """Condense processes by removing unrelated fields to save space."""
    plain = []
    for p in processes:
        plain.append(
            PlainProcess(
                name=p.name,
                version=p.version,
                replicas=p.replicas,
                type=p.type,
                command=p.runtime.proc_command,
                status=p.status,
                instances=[
                    PlainInstance(
                        name=inst.name,
                        version=inst.version,
                        process_type=inst.process_type,
                        state=inst.state,
                        ready=inst.ready,
                        restart_count=inst.restart_count,
                        image=inst.image,
                    )
                    for inst in p.instances
                ],
            )
        )
    return plain


@define
class PlainInstance:
    name: str
    version: int
    process_type: str
    state: str = ""
    ready: bool = True
    restart_count: int = 0
    image: str = ""

    @property
    def shorter_name(self) -> str:
        """Return a simplified name

        'ieod-x-gunicorn-deployment-59b9789f76wk82' -> '59b9789f76wk82'
        """
        return self.name.split("-")[-1]

    def is_ready_for(self, expected_version: int) -> bool:
        """detect if the instance if ready for the given version"""
        return self.ready and self.version == expected_version


@define
class PlainProcess:
    name: str
    version: int
    replicas: int
    type: str
    command: str
    status: Optional[Status] = None
    instances: List[PlainInstance] = field(factory=list)

    def is_all_ready(self, expected_version: int) -> bool:
        """detect if all instances are ready"""
        if expected_version != self.version:
            return False

        return sum(inst.is_ready_for(expected_version) for inst in self.instances) == self.replicas


@define
class CNativeProcessSpec:
    """云原生应用的进程 spec. 其属性与 paas_wl.bk_app.processes.serializers.ProcessSpecSLZ 一致(兼容), 用于进程管理页面展示

    TODO:
     - 理清云原生应用对 ProcessManager.list_processes_specs 的依赖.
     - 后续考虑字段设计合理性(命名规范性等), 云原生应用进程数据单独维护, 不再要求与 ProcessSpecSLZ 一致.
    """

    name: str
    target_replicas: int
    plan_name: str

    resource_limit: dict
    resource_requests: dict
    resource_limit_quota: dict = field(init=False)

    autoscaling: bool = field(init=False)
    scaling_config: Optional[dict] = None

    target_status: ProcessTargetStatus = field(init=False)
    max_replicas: int = DEFAULT_CNATIVE_MAX_REPLICAS

    def __attrs_post_init__(self):
        self.autoscaling = bool(self.scaling_config)

        self.resource_limit_quota = {
            "cpu": int(parse_quantity(self.resource_limit["cpu"]) * 1000),
            "memory": int(parse_quantity(self.resource_limit["memory"]) / (1024 * 1024)),
        }

        if self.target_replicas == 0:
            self.target_status = ProcessTargetStatus.STOP
        else:
            self.target_status = ProcessTargetStatus.START


def list_cnative_module_processes_specs(app: Application, environment: str) -> dict[str, list[dict]]:
    """根据云原生应用的运行环境, 查询其线上所有模块的进程 specs

    :param app: 应用
    :param environment: 运行环境
    :return: dict {module_name: 进程 specs}
    """
    module_processes_specs = {}

    for res in list_mres_by_env(app, environment):
        module_processes_specs[res.metadata.annotations[MODULE_NAME_ANNO_KEY]] = [
            asdict(spec) for spec in gen_cnative_process_specs(res, environment)
        ]

    return module_processes_specs


def gen_cnative_process_specs(res: BkAppResource, environment: str) -> list[CNativeProcessSpec]:
    """由线上 BkAppResource 模型, 生成云原生应用的进程 spec 列表

    :param res: 线上的 BkAppResource 模型
    :param environment: 运行环境
    """
    specs: list[CNativeProcessSpec] = []

    all_replicas = ReplicasReader(res).read_all(AppEnvName(environment))
    all_scaling_configs = AutoscalingReader(res).read_all(AppEnvName(environment))
    all_res_quotas = ResQuotaReader(res).read_all(AppEnvName(environment))

    for proc in res.spec.processes:
        res_quota = all_res_quotas[proc.name][0]

        target_replicas = all_replicas[proc.name][0]
        if target_replicas is None:
            target_replicas = 1

        spec = CNativeProcessSpec(
            name=proc.name,
            target_replicas=target_replicas,
            plan_name=res_quota["plan"],
            resource_limit=res_quota["limits"],
            resource_requests=res_quota["requests"],
            scaling_config=all_scaling_configs[proc.name][0],
        )
        specs.append(spec)
    return specs


class ProcessManager:
    """Manager for engine processes"""

    def __init__(self, env: ModuleEnvironment):
        self.env = env

    @cached_property
    def wl_app(self) -> WlApp:
        return self.env.wl_app

    def sync_processes_specs(self, processes: List[ProcessTmpl]):
        """Sync specs by plain ProcessSpec structure

        :param processes: plain process spec structure,
                          such as [{"name": "web", "command": "foo", "replicas": 1, "plan": "bar"}, ...]
                          where 'replicas' and 'plan' is optional
        """
        ProcessSpecManager(self.wl_app).sync(processes)

    def list_processes_specs(self, target_status: Optional[str] = None) -> List[Dict]:
        """Get specs of current app's all processes

        :param target_status: if given, filter results by given target_status
        """
        if self.wl_app.type == WlAppType.CLOUD_NATIVE:
            return self._list_cnative_specs(target_status)

        return self._list_default_specs(target_status)

    def list_processes_specs_for_legacy(self) -> List[Dict]:
        """Get specs of current app's all processes

        NOTE: 仅用于云原生应用未确认迁移时, 返回旧的进程信息
        不能直接使用 list_processes_specs 的原因是, self.wl_app.type 已是 WlAppType.CLOUD_NATIVE
        """
        return self._list_default_specs()

    def list_processes(self) -> List[Process]:
        """Query all running processes.

        :return: List[Process]:
                    A list of Process objects representing the status of each running process.
        """
        return list_processes(self.env).processes

    def list_plain_processes(self) -> List[PlainProcess]:
        """Query all running processes and return simplified status.

        :return: List[PlainProcess]:
                    A list of PlainProcess objects representing simplified status of each running process.
        """
        return condense_processes(self.list_processes())

    def get_running_image(self) -> str:
        images = {instance.image for process in self.list_processes() for instance in process.instances}
        if len(images) == 0:
            raise RuntimeError(f"Can't find running image for Env<{self.env}>")
        elif len(images) > 1:
            raise RuntimeError("multiple image found!")
        return images.pop()

    def create_webconsole(
        self, operator: str, process_type: str, process_instance_name: str, container_name=None, command="bash"
    ):
        """Create a webconsole provided by bcs"""
        if not container_name:
            container_name = process_kmodel.get_by_type(self.wl_app, type=process_type).main_container_name

        cluster = get_cluster_by_app(self.wl_app)
        # 获取应用的租户信息
        app_code = get_metadata(self.wl_app).get_paas_app_code()
        tenant_id = get_tenant_id_for_app(app_code)
        return bcs_client_cls(tenant_id).create_web_console_sessions(
            json={
                "namespace": self.wl_app.namespace,
                "pod_name": process_instance_name,
                "container_name": container_name,
                "command": command,
                "operator": operator,
            },
            path_params={
                "cluster_id": cluster.bcs_cluster_id,
                "project_id_or_code": cluster.bcs_project_id,
                "version": "v4",
            },
        )

    def get_instance_logs(
        self,
        process_type: str,
        instance_name: str,
        previous: bool,
        timestamps: bool = False,
        container_name: str | None = None,
        tail_lines: Optional[int] = None,
    ):
        """获取进程实例日志

        :param process_type: 进程类型
        :param instance_name: 进程实例名称
        :param previous: 是否获取上一次运行的日志
        :param timestamps: 是否在日志前添加时间戳
        :param container_name: 容器名称
        :param tail_lines: 获取日志末尾的行数
        :return: str
        :raise: InstanceNotFound when instance not found
        """
        if not container_name:
            container_name = process_kmodel.get_by_type(self.wl_app, type=process_type).main_container_name

        k8s_client = get_client_by_app(self.wl_app)

        try:
            rsp = KPod(k8s_client).get_log(
                name=instance_name,
                namespace=self.wl_app.namespace,
                previous=previous,
                timestamps=timestamps,
                container=container_name,
                tail_lines=tail_lines,
            )
        except ApiException as e:
            if e.status == 400 and "previous terminated container" in json.loads(e.body)["message"]:
                raise InstanceNotFound("Terminated container not found")
            elif e.status == 404:
                raise InstanceNotFound("Instance not found")
            else:
                raise

        return ensure_text(rsp.data)

    def get_instance_logs_stream(
        self,
        process_type: str,
        instance_name: str,
        container_name: str | None = None,
        since_seconds: Optional[int] = None,
        timestamps: bool = True,
    ):
        """获取进程实例日志流

        :param process_type: 进程类型
        :param instance_name: 进程实例名称
        :param container_name: 容器名称
        :param since_seconds: 获取日志的起始时间
        :param timestamps: 是否在日志前添加时间戳
        :return: Generator yielding log lines
        :raise: InstanceNotFound when instance not found
        """
        if not container_name:
            container_name = process_kmodel.get_by_type(self.wl_app, type=process_type).main_container_name

        params = {
            "name": instance_name,
            "namespace": self.wl_app.namespace,
            "container": container_name,
            "follow": True,
            "timestamps": timestamps,
        }
        if since_seconds:
            params["since_seconds"] = since_seconds

        k8s_client = get_client_by_app(self.wl_app)

        try:
            for line in KPod(k8s_client).get_log(**params):
                yield ensure_text(line)
        except ApiException as e:
            if e.status == 400 and "previous terminated container" in json.loads(e.body)["message"]:
                raise InstanceNotFound("Terminated container not found")
            elif e.status == 404:
                raise InstanceNotFound("Instance not found")
            else:
                raise

    def _list_default_specs(self, target_status: Optional[str] = None) -> list[dict]:
        """查询普通应用的进程 specs"""
        results = []
        specs = ProcessSpecSLZ(self.wl_app.process_specs.select_related("plan").all(), many=True).data
        for item in specs:
            # Filter by given conditions
            if target_status and item["target_status"] != target_status:
                continue
            results.append(item)
        return results

    def _list_cnative_specs(self, target_status: Optional[str] = None) -> list[dict]:
        """查询云原生应用的线上进程 specs"""
        res = get_mres_from_cluster(self.env)
        if not res:
            return []

        specs = []
        for spec in gen_cnative_process_specs(res, self.env.environment):
            if target_status and spec.target_status != target_status:
                continue
            specs.append(asdict(spec))
        return specs
