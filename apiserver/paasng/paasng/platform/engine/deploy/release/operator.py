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

import logging
import time
from typing import Optional

from django.db import IntegrityError

from paas_wl.bk_app.applications.models import Build
from paas_wl.bk_app.cnative.specs import svc_disc
from paas_wl.bk_app.cnative.specs.constants import DeployStatus
from paas_wl.bk_app.cnative.specs.models import AppModelDeploy, AppModelRevision
from paas_wl.bk_app.cnative.specs.mounts import deploy_volume_source
from paas_wl.bk_app.cnative.specs.resource import deploy as apply_bkapp_to_k8s
from paas_wl.bk_app.monitoring.bklog.shim import make_bk_log_controller
from paas_wl.bk_app.processes.shim import ProcessManager
from paas_wl.infras.resources.base.kres import KNamespace
from paas_wl.infras.resources.utils.basic import get_client_by_app
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.bkapp_model.manifest import get_bkapp_resource_for_deploy
from paasng.platform.engine.constants import JobStatus
from paasng.platform.engine.deploy.bg_command.tasks import exec_bkapp_hook
from paasng.platform.engine.deploy.bg_wait.wait_bkapp import DeployStatusHandler, WaitAppModelReady
from paasng.platform.engine.exceptions import StepNotInPresetListError
from paasng.platform.engine.models import DeployPhaseTypes
from paasng.platform.engine.models.deployment import Deployment
from paasng.platform.engine.workflow import DeployStep

logger = logging.getLogger(__name__)


class BkAppReleaseMgr(DeployStep):
    """BkApp(CRD) Release Step, will schedule the Deployment/Ingress and so on by k8s operator.
    The k8s operator is deployed at app cluster"""

    phase_type = DeployPhaseTypes.RELEASE

    def start(self):
        build = Build.objects.get(pk=self.deployment.build_id)
        with self.procedure("更新进程配置"):
            # Turn the processes into the corresponding type in paas_wl module
            procs = self.deployment.get_processes()
            proc_mgr = ProcessManager(self.engine_app.env)
            proc_mgr.sync_processes_specs(procs)
            proc_mgr.sync_processes_probes(procs)

        # 优先使用本次部署指定的 revision, 如果未指定, 则使用与构建产物关联 revision(由(源码提供的 bkapp.yaml 创建)
        revision = AppModelRevision.objects.get(pk=self.deployment.bkapp_revision_id or build.bkapp_revision_id)
        with self.procedure("部署应用"):
            bkapp_release_id = release_by_k8s_operator(
                self.module_environment,
                revision,
                operator=self.deployment.operator,
                build=build,
                deployment=self.deployment,
            )

        # 这里只是轮询开始，具体状态更新需要放到轮询组件中完成
        self.state_mgr.update(bkapp_release_id=bkapp_release_id)
        try:
            step_obj = self.phase.get_step_by_name(name="检测部署结果")
            step_obj.mark_and_write_to_stream(
                self.stream, JobStatus.PENDING, extra_info={"bkapp_release_id": bkapp_release_id}
            )
        except StepNotInPresetListError:
            logger.debug("Step not found or duplicated, name: %s", "检测部署结果")


def release_by_k8s_operator(
    env: ModuleEnvironment,
    revision: AppModelRevision,
    operator: str,
    build: Optional[Build] = None,
    deployment: Optional[Deployment] = None,
) -> str:
    """Create a new release for given environment(which will be handled by k8s operator).
    this action will start an async waiting procedure which waits for the release to be finished.

    :param env: The environment to create the release for.
    :param revision: The revision to be released.
    :param operator: current operator's user_id
    :param deployment: the deployment of the release

    :raises: ValueError when image credential_refs is invalid  TODO: 抛更具体的异常
    :raises: UnprocessibleEntityError when k8s can not process this manifest
    :raises: other unknown exceptions...
    """
    application = env.application
    module = env.module

    # TODO: read name from request data or generate by model resource payload
    # Add current timestamp in name to avoid conflicts
    default_name = f"{application.code}-{revision.pk}-{int(time.time())}"

    # The resource payload of the revision object won't be send to the operator directly,
    # the platform will construct a bk-app model for deploying instead. So the model
    # deploy object created below only can be treated as a deploy history record.
    try:
        app_model_deploy = AppModelDeploy.objects.create(
            application_id=application.id,
            module_id=module.id,
            environment_name=env.environment,
            name=default_name,
            revision=revision,
            status=DeployStatus.PENDING.value,
            operator=operator,
        )
    except IntegrityError:
        logger.warning("Name conflicts when creating new AppModelDeploy object, name: %s.", default_name)
        raise

    try:
        advanced_options = deployment.advanced_options if deployment else None
        bkapp_res = get_bkapp_resource_for_deploy(
            env,
            deploy_id=str(app_model_deploy.id),
            force_image=build.image if build else None,
            image_pull_policy=advanced_options.image_pull_policy if advanced_options else None,
            use_cnb=build.is_build_from_cnb() if build else False,
            deployment=deployment,
        )

        # 下发 k8s 资源前需要确保命名空间存在
        ensure_namespace(env)

        # Apply the ConfigMap resource related with service discovery
        #
        # NOTE: This action might break running pods that get svc-discovery data by
        # mounting the configmap as file, because some data might be removed in the
        # latest version. We should ask the application developer to handle this properly.
        #
        # TODO: There is no way to set svc-disc related spec currently.
        svc_disc.apply_configmap(env, bkapp_res)

        # 下发待挂载的 volume source
        deploy_volume_source(env)

        deployed_manifest = apply_bkapp_to_k8s(env, bkapp_res.to_deployable())

        # 下发日志采集配置
        ensure_bk_log_if_need(env)
    except Exception:
        app_model_deploy.status = DeployStatus.ERROR
        app_model_deploy.save(update_fields=["status", "updated"])
        raise

    revision.deployed_value = deployed_manifest
    revision.has_deployed = True
    revision.save(update_fields=["deployed_value", "has_deployed", "updated"])

    # TODO: 统计成功 metrics

    if bkapp_res.spec.hooks and bkapp_res.spec.hooks.preRelease and deployment:
        exec_bkapp_hook.delay(bkapp_res.metadata.name, app_model_deploy.id, deployment.id)

    # Poll status in background
    WaitAppModelReady.start(
        {"env_id": env.id, "deploy_id": app_model_deploy.id, "deployment_id": deployment.id if deployment else None},
        DeployStatusHandler,
    )
    return str(app_model_deploy.id)


def ensure_namespace(env: ModuleEnvironment, max_wait_seconds: int = 15) -> bool:
    """确保命名空间存在, 如果命名空间不存在, 那么将创建一个 Namespace 和 ServiceAccount

    :param env: ModuleEnvironment
    :param max_wait_seconds: 等待 ServiceAccount 就绪的时间
    :return: whether an namespace was created.
    """
    wl_app = env.wl_app
    with get_client_by_app(wl_app) as client:
        namespace_client = KNamespace(client)
        _, created = namespace_client.get_or_create(name=wl_app.namespace)
        if created:
            namespace_client.wait_for_default_sa(namespace=wl_app.namespace, timeout=max_wait_seconds)
        return created


def ensure_bk_log_if_need(env: ModuleEnvironment):
    """如果集群支持且应用声明了 BkLogConfig, 则尝试下发日志采集配置"""
    try:
        # 下发 BkLogConfig
        make_bk_log_controller(env).create_or_patch()
    except Exception:
        logger.exception("An error occur when creating BkLogConfig")
