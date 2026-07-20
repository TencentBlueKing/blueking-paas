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
from typing import Any, Dict, List, Tuple

from django.db import IntegrityError
from kubernetes.utils.quantity import parse_quantity

from paas_wl.bk_app.applications.models import Build
from paas_wl.bk_app.cnative.specs.addresses import save_addresses
from paas_wl.bk_app.cnative.specs.constants import BKPAAS_DEPLOY_ID_ANNO_KEY, DEFAULT_RES_QUOTA_PLAN_NAME, DeployStatus
from paas_wl.bk_app.cnative.specs.credentials import ImageCredentialsManager
from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppProcess, BkAppResource
from paas_wl.bk_app.cnative.specs.models import AppModelDeploy, AppModelRevision
from paas_wl.bk_app.sandbox_instance.entities import SandboxInstanceSpec
from paas_wl.bk_app.sandbox_instance.resource import SandboxInstanceManager
from paas_wl.core.resource import generate_bkapp_name, get_process_selector
from paas_wl.infras.cluster.shim import EnvClusterService
from paas_wl.infras.resources.kube_res.exceptions import AppEntityNotFound
from paas_wl.infras.resources.utils.basic import get_client_by_app
from paas_wl.workloads.images.kres_entities import ImageCredentials
from paas_wl.workloads.images.utils import make_image_pull_secret_name
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

# TODO: 确认后续如何支持 SIDECAR 模式
# AI Agent 应用采用单进程模型, 固定使用 web 进程承载 HTTP 服务
AI_AGENT_PROCESS_TYPE = "web"



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
        # 确保命名空间存在
        ensure_namespace(env)

        # 下发镜像拉取凭证 Secret(私有镜像场景必需)
        wl_app = env.wl_app
        with get_client_by_app(wl_app) as client:
            image_credentials = ImageCredentials.load_from_app(wl_app)
            ImageCredentialsManager(client).upsert(image_credentials, update_method="patch")

        # 下发 SandboxInstance CR(异步, 就绪由 poller 判定)
        cluster_name = EnvClusterService(env).get_cluster_name()
        spec = build_sandbox_spec_from_deploy(env, build, deployment, deploy_id=str(app_model_deploy.id))
        deployed_manifest = SandboxInstanceManager(cluster_name).deploy(spec)

        # 地址暴露: 平台侧自建 Service + Ingress 指向 cube Pod, 并写入地址 DB
        deploy_sandbox_networking(env)

        # 日志采集
        ensure_bk_log_if_need(env)
    except Exception:
        app_model_deploy.status = DeployStatus.ERROR
        app_model_deploy.save(update_fields=["status", "updated"])
        raise

    revision.deployed_value = deployed_manifest
    revision.has_deployed = True
    revision.save(update_fields=["deployed_value", "has_deployed", "updated"])

    # 后台轮询 SandboxInstance 就绪状态, 就绪后回填 AppModelDeploy.status
    WaitSandboxInstanceReady.start(
        {"env_id": env.id, "deploy_id": app_model_deploy.id, "deployment_id": deployment.id},
        DeployStatusHandler,
    )
    return str(app_model_deploy.id)


def build_sandbox_spec_from_deploy(
    env: ModuleEnvironment, build: Build, deployment: Deployment, deploy_id: str
) -> SandboxInstanceSpec:
    """从部署上下文拼装 SandboxInstanceSpec"""
    wl_app = env.wl_app
    advanced_options = deployment.advanced_options

    bkapp_res = get_bkapp_resource_for_deploy(
        env,
        deploy_id=deploy_id,
        deployment=deployment,
        force_image=build.image,
        image_pull_policy=advanced_options.image_pull_policy if advanced_options else None,
    )
    proc = _find_process(bkapp_res.spec.processes, AI_AGENT_PROCESS_TYPE)
    cpu_cores, memory = _resolve_resource_quota(proc.resQuotaPlan if proc else None)

    # 从 BkApp resource 中 resolve 当前环境适用的运行时配置
    env_name = env.environment
    env_vars = _resolve_env_vars_for_sandbox(bkapp_res, env_name)
    node_selector, tolerations = _resolve_scheduling_for_sandbox(bkapp_res)
    dns_nameservers, host_aliases = _resolve_domain_resolution_for_sandbox(bkapp_res)

    # 镜像拉取策略: 优先从部署选项取, 否则从 BkApp build 配置取, 兜底 IfNotPresent
    image_pull_policy = (
        (advanced_options.image_pull_policy if advanced_options else None)
        or (bkapp_res.spec.build.imagePullPolicy if bkapp_res.spec.build else None)
        or "IfNotPresent"
    )

    return SandboxInstanceSpec(
        name=generate_bkapp_name(env),
        namespace=wl_app.namespace,
        image=build.image,
        cpu_cores=cpu_cores,
        memory=memory,
        command=(proc.command or []) if proc else [],
        args=(proc.args or []) if proc else [],
        labels=get_process_selector(wl_app, AI_AGENT_PROCESS_TYPE),
        annotations={BKPAAS_DEPLOY_ID_ANNO_KEY: deploy_id},
        env_vars=env_vars,
        image_pull_policy=image_pull_policy,
        image_pull_secrets=[{"name": make_image_pull_secret_name(wl_app)}],
        node_selector=node_selector,
        tolerations=tolerations,
        dns_nameservers=dns_nameservers,
        host_aliases=host_aliases,
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
    plan_name = res_quota_plan or DEFAULT_RES_QUOTA_PLAN_NAME
    try:
        plan = ResQuotaPlan.objects.get(name=plan_name, is_active=True)
    except ResQuotaPlan.DoesNotExist:
        plan = ResQuotaPlan.objects.get(name=DEFAULT_RES_QUOTA_PLAN_NAME)

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


# ---------------------------------------------------------------------------
# BkApp → SandboxInstance 运行时配置 resolve 函数
# ---------------------------------------------------------------------------


def _resolve_env_vars_for_sandbox(bkapp_res: BkAppResource, env_name: str) -> List[Dict[str, str]]:
    """从 BkApp 中 resolve 出当前环境的最终环境变量列表。

    逻辑: 全局变量(spec.configuration.env) 为基础, 同名的环境专属变量
    (envOverlay.envVariables 中 envName 匹配当前环境) 覆盖之。
    返回标准 K8s env 结构: [{"name": ..., "value": ...}]
    """
    # 以全局变量为底
    env_map: Dict[str, str] = {}
    for var in bkapp_res.spec.configuration.env:
        env_map[var.name] = var.value

    # 环境专属覆盖
    overlay = bkapp_res.spec.envOverlay
    if overlay and overlay.envVariables:
        for overlay_var in overlay.envVariables:
            if overlay_var.envName == env_name:
                env_map[overlay_var.name] = overlay_var.value

    return [{"name": k, "value": v} for k, v in env_map.items()]



def _resolve_scheduling_for_sandbox(
    bkapp_res: BkAppResource,
) -> Tuple[Dict[str, str], List[Dict[str, Any]]]:
    """从 BkApp 中提取调度配置(nodeSelector / tolerations)。"""
    node_selector: Dict[str, str] = {}
    tolerations: List[Dict[str, Any]] = []

    schedule = bkapp_res.spec.schedule
    if not schedule:
        return node_selector, tolerations

    if schedule.nodeSelector:
        node_selector = dict(schedule.nodeSelector)

    if schedule.tolerations:
        for t in schedule.tolerations:
            toleration: Dict[str, Any] = {"key": t.key, "operator": t.operator}
            if t.value is not None:
                toleration["value"] = t.value
            if t.effect is not None:
                toleration["effect"] = t.effect
            if t.tolerationSeconds is not None:
                toleration["tolerationSeconds"] = t.tolerationSeconds
            tolerations.append(toleration)

    return node_selector, tolerations


def _resolve_domain_resolution_for_sandbox(
    bkapp_res: BkAppResource,
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """从 BkApp 中提取域名解析配置(nameservers / hostAliases)。"""
    dns_nameservers: List[str] = []
    host_aliases: List[Dict[str, Any]] = []

    domain_res = bkapp_res.spec.domainResolution
    if not domain_res:
        return dns_nameservers, host_aliases

    if domain_res.nameservers:
        dns_nameservers = list(domain_res.nameservers)

    if domain_res.hostAliases:
        for alias in domain_res.hostAliases:
            host_aliases.append({"ip": alias.ip, "hostnames": list(alias.hostnames)})

    return dns_nameservers, host_aliases
