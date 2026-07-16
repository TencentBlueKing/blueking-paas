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

"""AI Agent 应用的运行时下发链路: 用 SandboxInstance CR 替代 BkApp CR。

与 release_by_k8s_operator 的差异:
- 工作负载: 下发 SandboxInstance CR(由集群侧 sandbox-controller 渲染 cube Pod), 而非 BkApp CR。
- 网络暴露: 由于 SandboxInstance 绕过了 app-operator, DomainGroupMapping 无法复用
  (其 reconcile 硬依赖同名 BkApp 及 BkApp 创建的 Service)。因此这里由平台侧直接下发
  Service + Ingress 指向 cube Pod, 并复用 save_addresses 写入地址 DB。
- 部署历史/运行态/地址发现: 复用 AppModelDeploy + env_is_running + save_addresses 的既有资产。
"""

import logging
import math
import time
from typing import List, Tuple

from django.db import IntegrityError
from kubernetes.utils.quantity import parse_quantity

from paas_wl.bk_app.applications.models import Build
from paas_wl.bk_app.cnative.specs.addresses import save_addresses
from paas_wl.bk_app.cnative.specs.constants import DeployStatus
from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppProcess
from paas_wl.bk_app.cnative.specs.models import AppModelDeploy, AppModelRevision
from paas_wl.bk_app.sandbox_instance.entities import SandboxInstanceSpec
from paas_wl.bk_app.sandbox_instance.resource import SandboxInstanceManager
from paas_wl.core.resource import generate_bkapp_name, get_process_selector
from paas_wl.infras.cluster.shim import EnvClusterService
from paas_wl.infras.resources.kube_res.exceptions import AppEntityNotFound
from paas_wl.workloads.networking.ingress.kres_entities.service import service_kmodel
from paas_wl.workloads.networking.ingress.managers import AppDefaultIngresses
from paas_wl.workloads.networking.ingress.managers.service import build_process_service
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.bkapp_model.manifest import get_bkapp_resource_for_deploy
from paasng.platform.bkapp_model.models import ResQuotaPlan
from paasng.platform.engine.deploy.bg_wait.wait_bkapp import DeployStatusHandler
from paasng.platform.engine.deploy.bg_wait.wait_sandbox import WaitSandboxInstanceReady
from paasng.platform.engine.deploy.release.operator import ensure_bk_log_if_need, ensure_namespace
from paasng.platform.engine.models.deployment import Deployment

logger = logging.getLogger(__name__)

# AI Agent 应用采用单进程模型, 固定使用 web 进程承载 HTTP 服务
AI_AGENT_PROCESS_TYPE = "web"

# resQuotaPlan 未指定时的默认方案名, 与 ResQuotaPlan 内置数据一致
DEFAULT_RES_QUOTA_PLAN = "default"


def release_by_sandbox_instance(
    env: ModuleEnvironment, revision: AppModelRevision, operator: str, build: Build, deployment: Deployment
) -> str:
    """为 AI Agent 应用创建一次发布, 工作负载由 SandboxInstance CR 承载。

    :param env: 目标部署环境。
    :param revision: 本次发布的 AppModelRevision。
    :param operator: 操作人 user_id。
    :param build: 本次发布的构建产物。
    :param deployment: 本次发布的 Deployment 对象。
    :returns: AppModelDeploy.id 的字符串形式(与 release_by_k8s_operator 语义一致)。
    """
    application = env.application
    module = env.module

    default_name = f"{application.code}-{revision.pk}-{int(time.time())}"

    # 部署历史记录: 复用 AppModelDeploy, 满足 env_is_running(any_successful) 运行态判据
    try:
        app_model_deploy = AppModelDeploy.objects.create(
            application_id=application.id,
            module_id=module.id,
            environment_name=env.environment,
            name=default_name,
            revision=revision,
            status=DeployStatus.PENDING.value,
            operator=operator,
            tenant_id=application.tenant_id,
        )
    except IntegrityError:
        logger.warning("Name conflicts when creating new AppModelDeploy object, name: %s.", default_name)
        raise

    try:
        # 确保命名空间存在(与云原生对齐, 使用 env.wl_app.namespace)
        ensure_namespace(env)

        # 下发 SandboxInstance CR(异步, 就绪由 poller 判定)
        cluster_name = EnvClusterService(env).get_cluster_name()
        spec = build_sandbox_spec_from_deploy(env, build, deployment, deploy_id=str(app_model_deploy.id))
        SandboxInstanceManager(cluster_name).deploy(spec)

        # 地址暴露: 平台侧自建 Service + Ingress 指向 cube Pod, 并写入地址 DB
        deploy_sandbox_networking(env)

        # 日志采集
        ensure_bk_log_if_need(env)
    except Exception:
        app_model_deploy.status = DeployStatus.ERROR
        app_model_deploy.save(update_fields=["status", "updated"])
        raise

    revision.has_deployed = True
    revision.save(update_fields=["has_deployed", "updated"])

    # 后台轮询 SandboxInstance 就绪状态, 就绪后回填 AppModelDeploy.status
    WaitSandboxInstanceReady.start(
        {"env_id": env.id, "deploy_id": app_model_deploy.id, "deployment_id": deployment.id},
        DeployStatusHandler,
    )
    return str(app_model_deploy.id)


def build_sandbox_spec_from_deploy(
    env: ModuleEnvironment, build: Build, deployment: Deployment, deploy_id: str
) -> SandboxInstanceSpec:
    """从部署上下文拼装 SandboxInstanceSpec。

    - image: 取本次构建产物镜像。
    - cpu_cores / memory: 从 BkApp Model 的 web 进程 resQuotaPlan 解析。
    - command / args: 从 BkApp Model 的 web 进程读取。
    - namespace: 对齐云原生命名空间(env.wl_app.namespace), 使地址/日志链路可复用。
    - labels: 云原生 Service selector(module-name + process-name),
      sandbox-controller 会继承到 cube Pod, 从而被平台自建的 Service 选中。
    """
    wl_app = env.wl_app

    bkapp_res = get_bkapp_resource_for_deploy(
        env,
        deploy_id=deploy_id,
        deployment=deployment,
        force_image=build.image,
    )
    proc = _find_process(bkapp_res.spec.processes, AI_AGENT_PROCESS_TYPE)
    cpu_cores, memory = _resolve_resource_quota(proc.resQuotaPlan if proc else None)

    return SandboxInstanceSpec(
        name=generate_bkapp_name(env),
        namespace=wl_app.namespace,
        image=build.image,
        cpu_cores=cpu_cores,
        memory=memory,
        command=list(proc.command or []) if proc else [],
        args=list(proc.args or []) if proc else [],
        labels=get_process_selector(wl_app, AI_AGENT_PROCESS_TYPE),
    )


def deploy_sandbox_networking(env: ModuleEnvironment) -> None:
    """平台侧下发网络资源, 使 cube Pod 可通过 HTTP 访问。

    1. save_addresses: 写入应用访问地址到 DB(供 get_deployed_statuses / get_exposed_url 发现)。
    2. Service: 复用 build_process_service, selector 为云原生 module-name + process-name,
       选中带同名 label 的 cube Pod。
    3. Ingress: 复用 AppDefaultIngresses, 域名/路径取自 save_addresses 写入的 AppDomain/AppSubpath,
       backend 指向上面的 Service。
    """
    wl_app = env.wl_app

    # 1. 写入地址 DB
    save_addresses(env)

    # 2. 平台自建 Service(selector 已对齐云原生, 见 get_process_selector)
    service = build_process_service(wl_app, AI_AGENT_PROCESS_TYPE)
    try:
        service_kmodel.get(wl_app, service.name)
    except AppEntityNotFound:
        service_kmodel.create(service)

    # 3. 下发 Ingress, backend 指向自建 Service
    AppDefaultIngresses(wl_app).sync_ignore_empty(default_service_name=service.name)


def _find_process(processes: List[BkAppProcess], process_type: str):
    """从 BkApp 进程列表中按 name 查找进程, 找不到时回退到首个进程。"""
    for proc in processes:
        if proc.name == process_type:
            return proc
    return processes[0] if processes else None


def _resolve_resource_quota(res_quota_plan: str | None) -> Tuple[int, str]:
    """把 resQuotaPlan 解析为 (cpu_cores, memory)。

    ResQuotaPlan.limits 形如 {"cpu": "4000m", "memory": "1024Mi"}。
    - cpu: 转换为整数核数(SandboxInstance 的 cpu.cores 为整数)。
    - memory: 直接透传 K8s quantity 字符串。
    """
    plan_name = res_quota_plan or DEFAULT_RES_QUOTA_PLAN
    try:
        plan = ResQuotaPlan.objects.get(name=plan_name, is_active=True)
    except ResQuotaPlan.DoesNotExist:
        plan = ResQuotaPlan.objects.get(name=DEFAULT_RES_QUOTA_PLAN)

    limits = plan.limits or {}
    cpu_cores = _parse_cpu_cores(limits.get("cpu", "4000m"))
    memory = limits.get("memory", "1024Mi")
    return cpu_cores, memory


def _parse_cpu_cores(cpu: str) -> int:
    """把 K8s cpu quantity 解析为整数核数, 如 "4000m" -> 4, "2.5" -> 3。向上取整且至少 1 核。

    复用 kubernetes.utils.quantity.parse_quantity 解析(返回以「核」为单位的 Decimal),
    与项目内其它 CPU 解析(processes/serializers/manifest)保持一致。
    """
    cores = math.ceil(parse_quantity(str(cpu).strip()))
    return max(cores, 1)
