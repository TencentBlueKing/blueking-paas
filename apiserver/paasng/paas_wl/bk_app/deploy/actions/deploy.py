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
import logging
from typing import TYPE_CHECKING, Dict, List, Tuple

from django.core.exceptions import ObjectDoesNotExist
from kubernetes.dynamic.exceptions import ResourceNotFoundError

from paas_wl.bk_app.deploy.actions.exceptions import BuildMissingError
from paas_wl.bk_app.deploy.app_res.controllers import (
    NamespacesHandler,
    ProcessesHandler,
    ensure_image_credentials_secret,
)
from paas_wl.bk_app.monitoring.app_monitor.shim import make_bk_monitor_controller
from paas_wl.bk_app.monitoring.bklog.shim import make_bk_log_controller
from paas_wl.bk_app.processes.constants import ProcessTargetStatus
from paas_wl.bk_app.processes.managers import AppProcessManager
from paas_wl.infras.resources.base.exceptions import KubeException
from paas_wl.infras.resources.generation.mapper import MapperProcConfig, get_mapper_proc_config
from paas_wl.infras.resources.generation.version import AppResVerManager
from paasng.platform.applications.models import ModuleEnvironment

if TYPE_CHECKING:
    from paas_wl.bk_app.applications.models import Release

logger = logging.getLogger(__name__)


class DeployAction:
    def __init__(self, env: ModuleEnvironment, release: "Release", extra_envs: Dict):
        self.env = env
        self.wl_app = env.wl_app
        self.release = release
        self.extra_envs = extra_envs

        if not self.release.build:
            raise BuildMissingError(f"no build related to release, app_name={self.wl_app.name}")

        self.ns_handler = NamespacesHandler.new_by_app(self.wl_app)

    def perform(self):
        # update ProcessSpec.target_status to resume the process for those archived app
        self.wl_app.process_specs.update(target_status=ProcessTargetStatus.START.value)

        # create namespace and image credentials secret before deploy for image app.
        self.ns_handler.ensure_namespace(self.wl_app.namespace)
        ensure_image_credentials_secret(self.wl_app)
        # update deploy info in scheduler module
        processes = AppProcessManager(app=self.wl_app).assemble_processes(extra_envs=self.extra_envs)
        handler = ProcessesHandler.new_by_app(self.wl_app)
        try:
            handler.deploy(list(processes))
        except KubeException as e:
            self.release.fail(summary=f"deployed {str(self.release.uuid)[:7]} which failed for: {e}")
            raise
        finally:
            self.recycle_resource()
        self.ensure_bk_log_if_need()
        self.ensure_bk_monitor_if_need()

    def recycle_resource(self):
        """回收上一次发布可能产生的僵尸进程"""
        try:
            prev_release = self.release.get_previous()
        except ObjectDoesNotExist:
            return
        ObsoleteProcessesCleaner(self.release, prev_release).clean_up()

    def ensure_bk_monitor_if_need(self):
        """如果集群支持且应用声明需要接入蓝鲸监控, 则尝试下发监控配置"""
        try:
            # 下发 ServiceMonitor 配置
            make_bk_monitor_controller(self.wl_app).create_or_patch()
        except (KubeException, ResourceNotFoundError):
            logger.exception("An error occur when creating ServiceMonitor")

    def ensure_bk_log_if_need(self):
        """如果集群支持且应用声明了 BkLogConfig, 则尝试下发日志采集配置"""
        try:
            # 下发 BkLogConfig
            make_bk_log_controller(self.env).create_or_patch()
        except (KubeException, ResourceNotFoundError):
            logger.exception("An error occur when creating BkLogConfig")


class ObsoleteProcessesCleaner:
    """清理已经过期的进程资源（主要指 Deployment 与 Service）。

    目前，共有两种情况会产生过期的进程资源：

    - 用户修改了 process_type
    - 用户修改了 command_name( v1 mapper 的资源名依赖了 command_name)

    # NOTE: 暂时无法处理应用的 mapper version 发生变化的情况，比如从 v1 切换为 v2。
    # 未来也许可以通过读取上一次 release 的 version 来实现。

    :param curr_release: Current release object.
    :param prev_release: Previous release object.
    """

    def __init__(self, curr_release: "Release", prev_release: "Release"):
        self.curr_release = curr_release
        self.prev_release = prev_release

    def clean_up(self):
        """Clean up all obsolete process resources."""
        handler = ProcessesHandler.new_by_app(self.curr_release.app)
        for mapper_proc_config, should_remove_svc in self.find_all():
            try:
                logger.info("Cleaning process %s, remove-svc: %s", mapper_proc_config, should_remove_svc)
                handler.delete(mapper_proc_config, should_remove_svc)
            except Exception as e:
                summary = (
                    f"clean up process {mapper_proc_config.type} of {str(self.curr_release.uuid)[:7]} "
                    f"failed, error detail: {e}"
                )
                logger.exception(summary)
                self.curr_release.summary = summary
                self.curr_release.save(update_fields=["summary"])
                return

    def find_all(self) -> List[Tuple[MapperProcConfig, bool]]:
        """Find all obsolete processes.

        :return: A list of (MapperProcConfig, should_remove_svc) tuples, the first config
            object can be used for for removing process resources, the second boolean value
            indicates that whether the service should also be removed.
        """
        if not (self.prev_release and self.prev_release.build):
            return []

        logger.debug(
            "Finding obsolete procs, versions: %s <-> %s", self.curr_release.version, self.prev_release.version
        )
        curr_procfile = self.curr_release.get_procfile()
        prev_procfile = self.prev_release.get_procfile()

        results = []
        for prev_type in prev_procfile:
            proc_config = get_mapper_proc_config(self.prev_release, prev_type)
            # Check if the process type has been removed
            if prev_type not in curr_procfile:
                # In this case, the service should also be removed
                results.append((proc_config, True))
                continue

            # Compare the name of deployment resources, if changed, the old one should be removed.
            # This happens when the app is using a legacy mapper version and the resource name
            # depends on the command name.
            prev_deploy_name = self.get_deployment_name(proc_config)
            curr_deploy_name = self.get_deployment_name(get_mapper_proc_config(self.curr_release, prev_type))
            if prev_deploy_name != curr_deploy_name:
                # Don't remove the service resource
                results.append((proc_config, False))
        return results

    @staticmethod
    def get_deployment_name(proc_config: MapperProcConfig) -> str:
        """Get the name of deployment resource for the given process type."""
        mapper_version = AppResVerManager(proc_config.app).curr_version
        return mapper_version.proc_resources(proc_config).deployment_name
