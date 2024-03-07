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
from typing import TYPE_CHECKING

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.deploy.app_res.controllers import (
    BuildHandler,
    CommandHandler,
    NamespacesHandler,
    ProcAutoscalingHandler,
    ProcessesHandler,
)
from paas_wl.infras.resources.base.base import get_client_by_cluster_name
from paas_wl.workloads.autoscaling.kres_entities import ProcAutoscaling
from paas_wl.workloads.images.kres_entities import ImageCredentials, credentials_kmodel
from paas_wl.workloads.release_controller.hooks.kres_entities import Command

if TYPE_CHECKING:
    from paas_wl.infras.resources.base.base import EnhancedApiClient
    from paasng.platform.engine.configurations.building import SlugBuilderTemplate

logger = logging.getLogger(__name__)


class K8sScheduler:
    def __init__(self, client: "EnhancedApiClient"):
        self.client = client
        self._initial_controllers(self.client)

    @classmethod
    def from_cluster_name(cls, cluster_name: str) -> "K8sScheduler":
        """Create a scheduler client from context name"""
        client = get_client_by_cluster_name(cluster_name)
        return cls(client)

    def _initial_controllers(self, client: "EnhancedApiClient"):
        # scheduler will not operate k8s resource directly, but
        # assigning the task to several controllers
        self.processes_handler = ProcessesHandler(client)
        self.build_handler = BuildHandler(client)
        self.namespace_handler = NamespacesHandler(client)
        self.command_handler = CommandHandler(client)
        self.credential_handler = credentials_kmodel
        self.autoscaling_handler = ProcAutoscalingHandler(client)

    #############
    # build API #
    #############

    def build_slug(self, template: "SlugBuilderTemplate") -> str:
        """Build a default slug in NeverRestart Pod, called by Builder
        used to build on Job, but job doesn't meet our needs

        :returns: name of slug build pod
        """
        return self.build_handler.build_slug(template=template)

    def get_build_log(self, namespace, name, timeout, **kwargs):
        return self.build_handler.get_build_log(namespace, name, timeout=timeout, **kwargs)

    def wait_build_succeeded(self, *args, **kwargs):
        return self.build_handler.wait_for_succeeded(*args, **kwargs)

    def wait_build_logs_readiness(self, *args, **kwargs):
        return self.build_handler.wait_for_logs_readiness(*args, **kwargs)

    def delete_builder(self, namespace, name):
        """Recycle an existing slug-builder pod unless it's running"""
        return self.build_handler.delete_slug(namespace=namespace, name=name)

    def interrupt_builder(self, namespace, name):
        return self.build_handler.interrupt_builder(namespace=namespace, name=name)

    ###############
    # command API #
    ###############
    def run_command(self, command: Command) -> str:
        """run a command in NeverRestart Pod."""
        self.ensure_namespace(command.app.namespace)
        self.ensure_image_credentials_secret(command.app)
        return self.command_handler.run_command(command)

    def delete_command(self, command: Command):
        return self.command_handler.delete_command(command)

    def interrupt_command(self, command: Command):
        return self.command_handler.interrupt_command(command)

    def wait_command_succeeded(self, command: Command, timeout: int):
        return self.command_handler.wait_for_succeeded(command=command, timeout=timeout)

    def wait_command_logs_readiness(self, command: Command, timeout: int):
        return self.command_handler.wait_for_logs_readiness(command=command, timeout=timeout)

    def get_command_logs(self, command: Command, timeout: int, follow: bool = False):
        return self.command_handler.get_command_logs(command, timeout, follow=follow)

    #################
    # namespace API #
    #################

    def ensure_namespace(self, namespace: str, max_wait_seconds: int = 15):
        """确保命名空间存在, 如果命名空间不存在, 那么将创建一个 Namespace 和 ServiceAccount

        :param namespace: 需要确保存在的 namespace
        :param max_wait_seconds: 等待 ServiceAccount 就绪的时间
        :return:
        """
        self.namespace_handler.create(namespace)
        self.namespace_handler.check_service_account_secret(namespace, max_wait_seconds=max_wait_seconds)

    def delete_all_under_namespace(self, namespace: str):
        """k8s 直接删除 namespace 将清除其下所有资源"""
        self.namespace_handler.delete(namespace)

    ####################
    # image secret API #
    ####################
    def ensure_image_credentials_secret(self, app: WlApp):
        """确保应用镜像的访问凭证存在"""
        credentials = ImageCredentials.load_from_app(app)
        self.credential_handler.upsert(credentials, update_method="patch")

    ###################
    # autoscaling API #
    ###################
    def deploy_autoscaling(self, scaling: ProcAutoscaling):
        """为某进程下发/更新自动扩缩容配置"""
        self.autoscaling_handler.deploy(scaling)

    def disable_autoscaling(self, scaling: ProcAutoscaling):
        """移除某进程的自动扩缩容配置, 若资源原本不存在，则跳过"""
        self.autoscaling_handler.delete(scaling)
