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
from typing import Dict, Optional

from django.conf import settings

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.deploy.app_res.utils import get_scheduler_client_by_app
from paas_wl.bk_app.devcontainer.entities import ContainerDetail, HealthPhase, Resources, ResourceSpec, Runtime
from paas_wl.bk_app.devcontainer.kres_entities import DevContainer, DevContainerIngress, DevContainerService
from paas_wl.bk_app.devcontainer.kres_entities.container import get_container_name
from paas_wl.bk_app.devcontainer.kres_entities.ingress import get_ingress_name
from paas_wl.infras.resources.kube_res.base import AppEntityManager
from paas_wl.infras.resources.kube_res.exceptions import AppEntityNotFound
from paasng.platform.applications.models import Application
from paasng.platform.modules.constants import DEFAULT_ENGINE_APP_PREFIX, ModuleName

from .exceptions import DevContainerAlreadyExists, DevContainerResourceNotFound


class DevContainerController:
    """DevContainer Controller

    :param app: Application 实例
    :param module_name: 模块名称
    :param dev_wl_app: WlApp 实例. 默认为 None. 为 None 时, 会根据 app 和 module_name 创建 WlApp 实例
    """

    container_mgr: AppEntityManager[DevContainer] = AppEntityManager[DevContainer](DevContainer)
    service_mgr: AppEntityManager[DevContainerService] = AppEntityManager[DevContainerService](DevContainerService)
    ingress_mgr: AppEntityManager[DevContainerIngress] = AppEntityManager[DevContainerIngress](DevContainerIngress)

    def __init__(self, app: Application, module_name: str, dev_wl_app: Optional[WlApp] = None):
        self.app = app
        self.dev_wl_app: WlApp = dev_wl_app or _DevWlAppCreator(app, module_name).create()

        assert module_name == self.dev_wl_app.module_name

    def deploy(self, envs: Dict[str, str]):
        """部署 devcontainer"""
        container_name = get_container_name(self.dev_wl_app)
        try:
            self.container_mgr.get(self.dev_wl_app, container_name)
        except AppEntityNotFound:
            self._deploy(envs)
        else:
            raise DevContainerAlreadyExists(f"devcontainer {container_name} already exists")

    def delete(self):
        """通过直接删除命名空间的方式, 销毁 devcontainer 服务"""
        scheduler_client = get_scheduler_client_by_app(app=self.dev_wl_app)
        scheduler_client.delete_all_under_namespace(namespace=self.dev_wl_app.namespace)

    def get_container_detail(self) -> ContainerDetail:
        """获取 devcontainer 详情"""
        try:
            ingress_entity: DevContainerIngress = self.ingress_mgr.get(
                self.dev_wl_app, get_ingress_name(self.dev_wl_app)
            )
        except AppEntityNotFound:
            raise DevContainerResourceNotFound("devcontainer url not found")

        url = ingress_entity.domains[0].host

        try:
            container_entity: DevContainer = self.container_mgr.get(
                self.dev_wl_app, get_container_name(self.dev_wl_app)
            )
        except AppEntityNotFound:
            raise DevContainerResourceNotFound("devcontainer not found")

        status = container_entity.status.to_health_phase() if container_entity.status else HealthPhase.UNKNOWN
        return ContainerDetail(url=url, envs=container_entity.runtime.envs, status=status)

    def _deploy(self, envs: Dict[str, str]):
        """部署 devcontainer 服务

        步骤:
        1. ensure namespace
        2. create Container deployment
        3. upsert service
        4. upsert ingress
        """
        scheduler_client = get_scheduler_client_by_app(app=self.dev_wl_app)
        scheduler_client.ensure_namespace(namespace=self.dev_wl_app.namespace)

        default_resources = Resources(
            limits=ResourceSpec(cpu="4", memory="2Gi"),
            requests=ResourceSpec(cpu="200m", memory="512Mi"),
        )

        container_entity = DevContainer.create(
            self.dev_wl_app,
            runtime=Runtime(envs=envs, image=settings.DEVCONTAINER_IMAGE),
            resources=default_resources,
        )
        self.container_mgr.create(container_entity)

        service_entity = DevContainerService.create(self.dev_wl_app)
        self.service_mgr.upsert(service_entity)

        ingress_entity = DevContainerIngress.create(self.dev_wl_app, self.app.code)
        self.ingress_mgr.upsert(ingress_entity)


class _DevWlAppCreator:
    """WlApp 实例构造器"""

    def __init__(self, app: Application, module_name: str):
        self.app = app
        self.module_name = module_name

    def create(self) -> WlApp:
        """创建 WlApp 实例"""
        dev_wl_app = WlApp(region=self.app.region, name=self._make_dev_wl_app_name(), type=self.app.type)

        # 因为 dev_wl_app 不是查询集结果, 所以需要覆盖 namespace 和 module_name, 以保证 AppEntityManager 模式能够正常工作
        dev_wl_app.namespace = f"{DEFAULT_ENGINE_APP_PREFIX}-{self.app.code}-dev".replace("_", "0us0")
        dev_wl_app.module_name = self.module_name

        return dev_wl_app

    def _make_dev_wl_app_name(self) -> str:
        """参考 make_engine_app_name 规则, 生成 dev 环境的 WlApp name"""
        if self.module_name == ModuleName.DEFAULT.value:
            return f"{DEFAULT_ENGINE_APP_PREFIX}-{self.app.code}-dev"
        else:
            return f"{DEFAULT_ENGINE_APP_PREFIX}-{self.app.code}-m-{self.module_name}-dev"
