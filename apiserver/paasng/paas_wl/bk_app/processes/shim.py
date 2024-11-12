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
from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.cnative.specs.constants import MODULE_NAME_ANNO_KEY, ResQuotaPlan
from paas_wl.bk_app.cnative.specs.crd.bk_app import AutoscalingSpec, BkAppResource
from paas_wl.bk_app.cnative.specs.procs.quota import PLAN_TO_LIMIT_QUOTA_MAP, PLAN_TO_REQUEST_QUOTA_MAP
from paas_wl.bk_app.cnative.specs.resource import BkAppResourceByEnvLister, get_mres_from_cluster
from paas_wl.bk_app.processes.constants import DEFAULT_CNATIVE_MAX_REPLICAS, ProcessTargetStatus
from paas_wl.bk_app.processes.controllers import Process, list_processes
from paas_wl.bk_app.processes.exceptions import PreviousInstanceNotFound
from paas_wl.bk_app.processes.models import ProcessProbeManager, ProcessSpecManager
from paas_wl.bk_app.processes.processes import PlainProcess, condense_processes
from paas_wl.bk_app.processes.readers import process_kmodel
from paas_wl.bk_app.processes.serializers import ProcessSpecSLZ
from paas_wl.infras.cluster.utils import get_cluster_by_app
from paas_wl.infras.resources.base.bcs_client import BCSClient
from paas_wl.infras.resources.base.kres import KPod
from paas_wl.infras.resources.utils.basic import get_client_by_app
from paasng.platform.applications.models import Application, ModuleEnvironment
from paasng.platform.engine.models.deployment import ProcessTmpl


@define
class _CNativeProcessSpec:
    """云原生应用的进程 spec. 其属性与 paas_wl.bk_app.processes.serializers.ProcessSpecSLZ 一致(兼容)"""

    name: str
    target_replicas: int
    plan_name: str

    scaling_config: Optional[dict] = None
    autoscaling: bool = field(init=False)

    resource_limit: dict = field(init=False)
    resource_requests: dict = field(init=False)
    resource_limit_quota: dict = field(init=False)

    target_status: ProcessTargetStatus = field(init=False)
    max_replicas: int = DEFAULT_CNATIVE_MAX_REPLICAS

    def __attrs_post_init__(self):
        self.autoscaling = bool(self.scaling_config)

        # TODO 云原生应用的 requests 取值策略在 operator 中实现. 这里的值并非实际生效值, 仅用于前端展示. 如果需要, 后续校正?
        self.resource_requests = asdict(PLAN_TO_REQUEST_QUOTA_MAP[ResQuotaPlan(self.plan_name)])
        self.resource_limit = asdict(PLAN_TO_LIMIT_QUOTA_MAP[ResQuotaPlan(self.plan_name)])
        self.resource_limit_quota = {
            "cpu": int(parse_quantity(self.resource_limit["cpu"]) * 1000),
            "memory": int(parse_quantity(self.resource_limit["memory"]) / (1024 * 1024)),
        }

        if self.target_replicas == 0:
            self.target_status = ProcessTargetStatus.STOP
        else:
            self.target_status = ProcessTargetStatus.START


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

    def sync_processes_probes(self, processes: List[ProcessTmpl]):
        """Sync probes by plain ProcessProbe structure"""
        ProcessProbeManager(self.wl_app).sync(processes)

    def list_processes_specs(self, target_status: Optional[str] = None) -> List[Dict]:
        """Get specs of current app's all processes

        :param target_status: if given, filter results by given target_status
        """
        if self.wl_app.type == WlAppType.CLOUD_NATIVE:
            return self._list_cnative_specs(target_status)

        return self._list_default_specs(target_status)

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
        return BCSClient().api.create_web_console_sessions(
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

    def get_previous_logs(
        self,
        process_type: str,
        instance_name: str,
        container_name=None,
        tail_lines: Optional[int] = None,
    ):
        """获取进程实例上一次运行时日志

        :param process_type: 进程类型
        :param instance_name: 进程实例名称
        :param container_name: 容器名称
        :param tail_lines: 获取日志末尾的行数
        :return: str
        :raise: PreviousInstanceNotFound when previous instance not found
        """
        if not container_name:
            container_name = process_kmodel.get_by_type(self.wl_app, type=process_type).main_container_name

        k8s_client = get_client_by_app(self.wl_app)

        try:
            response = KPod(k8s_client).get_log(
                name=instance_name,
                namespace=self.wl_app.namespace,
                container=container_name,
                previous=True,
                tail_lines=tail_lines,
            )
        except ApiException as e:
            # k8s 没有找到上一个终止的容器
            if e.status == 400 and "previous terminated container" in json.loads(e.body)["message"]:
                raise PreviousInstanceNotFound
            else:
                raise

        return ensure_text(response.data)

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
        for spec in _gen_cnative_process_specs(res, self.env.environment):
            if target_status and spec.target_status != target_status:
                continue
            specs.append(asdict(spec))
        return specs


def list_cnative_module_processes_specs(app: Application, environment: str) -> dict[str, list[dict]]:
    """根据云原生应用的运行环境, 查询其线上所有模块的进程 specs

    :param app: 应用
    :param environment: 运行环境
    :return: dict {module_name: 进程 specs}
    """
    module_processes_specs = {}

    res_list: list[BkAppResource] = BkAppResourceByEnvLister(app, environment).list()
    for res in res_list:
        module_processes_specs[res.metadata.annotations[MODULE_NAME_ANNO_KEY]] = [
            asdict(spec) for spec in _gen_cnative_process_specs(res, environment)
        ]

    return module_processes_specs


def _gen_cnative_process_specs(res: BkAppResource, environment: str) -> list[_CNativeProcessSpec]:
    """解析线上 BkAppResource 模型, 生成云原生应用的进程 spec 列表

    :param res: 线上的 BkAppResource 模型
    :param environment: 运行环境
    """
    specs: list[_CNativeProcessSpec] = []
    env_overlay = res.spec.envOverlay

    env_autoscaling = {}
    env_replicas = {}
    env_quota_plan = {}

    if env_overlay:
        for replica in env_overlay.replicas or []:
            env_replicas[(replica.envName, replica.process)] = replica.count
        for quota in env_overlay.resQuotas or []:
            env_quota_plan[(quota.envName, quota.process)] = quota.plan
        for _autoscaling in env_overlay.autoscaling or []:
            env_autoscaling[(_autoscaling.envName, _autoscaling.process)] = AutoscalingSpec(
                minReplicas=_autoscaling.minReplicas, maxReplicas=_autoscaling.maxReplicas, policy=_autoscaling.policy
            )

    for proc in res.spec.processes:
        target_replicas = env_replicas.get((environment, proc.name), proc.replicas or 1)
        plan_name = env_quota_plan.get((environment, proc.name), str(proc.resQuotaPlan or ResQuotaPlan.P_DEFAULT))
        autoscaling: Optional[AutoscalingSpec] = env_autoscaling.get((environment, proc.name), proc.autoscaling)
        scaling_config = (
            {
                "min_replicas": autoscaling.minReplicas,
                "max_replicas": autoscaling.maxReplicas,
                "policy": autoscaling.policy,
            }
            if autoscaling
            else None
        )

        spec = _CNativeProcessSpec(
            name=proc.name, target_replicas=target_replicas, plan_name=plan_name, scaling_config=scaling_config
        )
        specs.append(spec)
    return specs
