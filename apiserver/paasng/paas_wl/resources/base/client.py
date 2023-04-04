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
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Iterable, List, Optional

from django.conf import settings
from kubernetes.dynamic.resource import ResourceInstance

from paas_wl.networking.ingress.managers.service import ProcDefaultServices
from paas_wl.platform.applications.models import WlApp
from paas_wl.release_controller.hooks.entities import Command
from paas_wl.resources.base.base import get_client_by_cluster_name
from paas_wl.resources.base.controllers import BuildHandler, CommandHandler, NamespacesHandler, ProcessesHandler
from paas_wl.resources.base.generation import get_mapper_version
from paas_wl.resources.base.kres import KNode, set_default_options
from paas_wl.workloads.images.entities import ImageCredentials, credentials_kmodel
from paas_wl.workloads.processes.models import Process

if TYPE_CHECKING:
    from paas_wl.resources.base.base import EnhancedApiClient
    from paas_wl.resources.base.generation import MapperPack
    from paasng.engine.configurations.building import SlugBuilderTemplate

logger = logging.getLogger(__name__)


@dataclass
class K8sScheduler:
    client: 'EnhancedApiClient'
    default_connect_timeout: int
    default_read_timeout: int
    mapper_version: Optional['MapperPack'] = None

    def __post_init__(self):
        # NOTE: dynamic client only support a single timeout parameter, use summed value as
        # the total timeout seconds.
        default_request_timeout = self.default_connect_timeout + self.default_read_timeout
        set_default_options({"request_timeout": default_request_timeout})

        # 主要通过上层判断传入 version
        self.mapper_version = self.mapper_version or get_mapper_version(
            target=settings.GLOBAL_DEFAULT_MAPPER_VERSION, init_kwargs={'client': self.client}
        )

        handler_init_params = dict(
            client=self.client,
            default_connect_timeout=self.default_connect_timeout,
            default_request_timeout=default_request_timeout,
            mapper_version=self.mapper_version,
        )
        self._initial_controllers(handler_init_params)

    @classmethod
    def from_cluster_name(cls, cluster_name: str) -> 'K8sScheduler':
        """Create a scheduler client from context name"""
        default_connect_timeout = settings.K8S_DEFAULT_CONNECT_TIMEOUT
        default_read_timeout = settings.K8S_DEFAULT_READ_TIMEOUT
        client = get_client_by_cluster_name(cluster_name)
        return cls(client, default_connect_timeout, default_read_timeout)

    def _initial_controllers(self, init_params: Dict):
        # scheduler will not operate k8s resource directly, but
        # assigning the task to several controllers
        self.processes_handler = ProcessesHandler(**init_params)
        self.build_handler = BuildHandler(**init_params)
        self.namespace_handler = NamespacesHandler(**init_params)
        self.command_handler = CommandHandler(**init_params)
        self.credential_handler = credentials_kmodel

    # Node start
    # WARNING: Node methods returns the raw data structure from kubernetes instead of transform it

    def get_nodes(self) -> List[ResourceInstance]:
        """Return a list a all kubernetes nodes in current cluster"""
        return KNode(self.client).ops_label.list({}).items

    def sync_state_to_nodes(self, state):
        """Sync a RegionClusterState object to current cluster, which means:

        - Update the labels of all nodes
        - Engine apps may use the labels to customize their schedule strategy
        """
        labels = state.to_labels()
        for node_name in state.nodes_name:
            node = KNode(self.client).get(node_name)
            node.metadata.labels = {**node.metadata.get('labels', {}), **labels}
            logger.debug(f"Patching node object {node_name} with labels {labels}")
            KNode(self.client).ops_name.replace_or_patch(node_name, node, update_method="patch")

    # Node End

    #################
    # processes API #
    #################

    def deploy_processes(self, processes: List[Process], **kwargs):
        """Deploy processes will create the Deployment and the Service"""
        for process in processes:
            self.processes_handler.deploy(process=process)
            ProcDefaultServices(process).create_or_patch()

    def scale_processes(self, processes: Iterable[Process]):
        """Scale Processes will patch the Deployment and Service"""
        for process in processes:
            ProcDefaultServices(process).create_or_patch()
            self.processes_handler.scale(process=process)

    def shutdown_processes(self, processes: Iterable[Process]):
        """Shutdown process will set the replicas to zero, but not delete the Deployment"""
        for process in processes:
            process.replicas = 0
            self.processes_handler.scale(process=process)

    def delete_processes(self, processes: List[Process], with_access=True):
        """Delete process will delete the Deployment and the Service(if with_access=True)"""
        for process in processes:
            if with_access:
                ProcDefaultServices(process).remove()
            self.processes_handler.delete(process=process)

    #############
    # build API #
    #############

    def build_slug(self, template: 'SlugBuilderTemplate') -> str:
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

    def ensure_namespace(self, namespace: str, max_wait_seconds: int = 10):
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
        self.credential_handler.upsert(credentials)
