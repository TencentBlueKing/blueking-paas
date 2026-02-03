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
from typing import TYPE_CHECKING, Dict

from django.conf import settings
from django.utils.encoding import force_str

from paas_wl.bk_app.deploy.app_res.controllers import NamespacesHandler
from paas_wl.infras.cluster.allocator import ClusterAllocator
from paas_wl.infras.cluster.entities import AllocationContext
from paas_wl.infras.resources.base.base import get_client_by_cluster_name
from paas_wl.infras.resources.kube_res.base import Schedule
from paas_wl.utils.text import b64encode
from paasng.misc.tools.smart_app.output import make_channel_stream
from paasng.platform.engine.constants import JobStatus
from paasng.platform.engine.deploy.bg_build.utils import get_envs_from_pypi_url

from .flow import SmartBuildStateMgr
from .handler import ContainerRuntimeSpec, SmartBuilderTemplate, SmartBuildHandler

if TYPE_CHECKING:
    from paasng.misc.tools.smart_app.models import SmartBuildRecord
    from paasng.misc.tools.smart_app.output import SmartBuildStream

logger = logging.getLogger(__name__)


class SmartAppBuilder:
    """The main controller for building a s-mart app package"""

    def __init__(
        self,
        smart_build: "SmartBuildRecord",
        source_get_url: str,
        dest_put_url: str,
    ):
        self.smart_build = smart_build
        self.source_get_url = source_get_url
        self.dest_put_url = dest_put_url

        self.stream: "SmartBuildStream" = make_channel_stream(smart_build)
        self.state_mgr = SmartBuildStateMgr.from_smart_build_id(smart_build.uuid, self.stream)

    def start(self):
        """Start the s-mart building process"""

        builder_name = None
        try:
            self.state_mgr.start()
            # 启动构建进程
            builder_name = self.launch_build_process()
            # 同步阻塞获取构建日志
            self.start_following_logs(builder_name)
            self.state_mgr.finish(JobStatus.SUCCESSFUL)
        except Exception as e:
            self.state_mgr.finish(JobStatus.FAILED, str(e))
        finally:
            self.stream.close()
            self.cleanup_builder_pod(builder_name)
            self.state_mgr.coordinator.release_lock(self.smart_build)

    def start_following_logs(self, builder_name: str):
        """Retrieve the build logs, and check the Pod execution status."""

        namespace = self._get_default_builder_namespace()
        cluster_name = self._get_default_cluster_name()
        handler = SmartBuildHandler(get_client_by_cluster_name(cluster_name))

        handler.wait_for_logs_readiness(namespace, builder_name, settings.SMART_BUILD_PROCESS_TIMEOUT)

        for raw_line in handler.get_build_log(
            namespace=namespace, name=builder_name, follow=True, timeout=settings.SMART_BUILD_PROCESS_TIMEOUT
        ):
            self.stream.write_message(force_str(raw_line))

        handler.wait_for_succeeded(namespace=namespace, name=builder_name, timeout=60)

    def launch_build_process(self) -> str:
        """launch the build Pod and return the Pod name"""

        envs: Dict[str, str] = {
            "SOURCE_GET_URL": self.source_get_url,
            "DEST_PUT_URL": self.dest_put_url,
            "BUILDER_SHIM_IMAGE": settings.SMART_BUILDER_SHIM_IMAGE,
            "PACKAGING_VERSION": self.smart_build.packaging_version,
        }

        # 添加缓存配置
        envs["CACHE_REGISTRY"] = f"{settings.SMART_DOCKER_REGISTRY_HOST}/{settings.SMART_DOCKER_REGISTRY_NAMESPACE}"
        username, password = settings.SMART_DOCKER_REGISTRY_USERNAME, settings.SMART_DOCKER_REGISTRY_PASSWORD
        envs["REGISTRY_AUTH"] = (
            f'{{"{settings.SMART_DOCKER_REGISTRY_HOST}": "Basic {b64encode(f"{username}:{password}")}"}}'
        )

        # Inject pip index url
        if settings.PYTHON_BUILDPACK_PIP_INDEX_URL:
            envs.update(get_envs_from_pypi_url(settings.PYTHON_BUILDPACK_PIP_INDEX_URL))

        # Inject extra env vars in settings for development purpose
        if settings.BUILD_EXTRA_ENV_VARS:
            envs.update(settings.BUILD_EXTRA_ENV_VARS)

        cluster_name = self._get_default_cluster_name()

        runtime = ContainerRuntimeSpec(
            image=settings.SMART_BUILDER_IMAGE,
            envs=envs,
        )

        schedule = Schedule(
            cluster_name=cluster_name,
            tolerations=[],
            node_selector={},
        )

        namespace = self._get_default_builder_namespace()
        pod_name = self._generate_builder_name(self.smart_build)

        client = get_client_by_cluster_name(cluster_name)
        NamespacesHandler(client).ensure_namespace(namespace)

        builder_template = SmartBuilderTemplate(
            name=pod_name,
            namespace=namespace,
            runtime=runtime,
            schedule=schedule,
        )

        smart_build_handler = SmartBuildHandler(client)
        return smart_build_handler.build_pod(template=builder_template)

    def cleanup_builder_pod(self, builder_name: str | None):
        """Clean up the builder pod after build process finished"""

        if not builder_name:
            return

        try:
            namespace = self._get_default_builder_namespace()
            cluster_name = self._get_default_cluster_name()
            handler = SmartBuildHandler(get_client_by_cluster_name(cluster_name))
            handler.delete_builder(namespace, builder_name, force=True)
        except Exception:
            # Log but don't raise, cleanup failure should not affect the build result
            logger.exception("Failed to cleanup builder pod %s", builder_name)

    @staticmethod
    def _get_default_cluster_name() -> str:
        """Get the default cluster name to run smart builder pods"""

        cluster = ClusterAllocator(AllocationContext.create_for_build_app()).get_default()
        return cluster.name

    @staticmethod
    def _generate_builder_name(smart_build: "SmartBuildRecord") -> str:
        """Get the s-mart builder name"""

        return f"builder-{smart_build.app_code.replace('_', '0us0')}-{smart_build.operator}"

    @staticmethod
    def _get_default_builder_namespace() -> str:
        """Get the namespace of s-mart builder pod"""

        return "smart-app-builder"
