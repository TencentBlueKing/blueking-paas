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
from typing import Dict

from django.conf import settings

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.deploy.app_res.controllers import NamespacesHandler
from paas_wl.bk_app.dev_sandbox.entities import DevSandboxDetail, HealthPhase, Resources, ResourceSpec, Runtime
from paas_wl.bk_app.dev_sandbox.kres_entities import (
    DevSandbox,
    DevSandboxIngress,
    DevSandboxService,
    get_dev_sandbox_name,
    get_ingress_name,
)
from paas_wl.infras.resources.kube_res.base import AppEntityManager
from paas_wl.infras.resources.kube_res.exceptions import AppEntityNotFound
from paasng.platform.applications.models import Application
from paasng.platform.modules.constants import DEFAULT_ENGINE_APP_PREFIX, ModuleName

from .exceptions import DevSandboxAlreadyExists, DevSandboxResourceNotFound


class DevSandboxController:
    """DevSandbox Controller

    :param app: Application 实例
    :param module_name: 模块名称
    """

    sandbox_mgr: AppEntityManager[DevSandbox] = AppEntityManager[DevSandbox](DevSandbox)
    service_mgr: AppEntityManager[DevSandboxService] = AppEntityManager[DevSandboxService](DevSandboxService)
    ingress_mgr: AppEntityManager[DevSandboxIngress] = AppEntityManager[DevSandboxIngress](DevSandboxIngress)

    def __init__(self, app: Application, module_name: str):
        self.app = app
        self.dev_wl_app: WlApp = _DevWlAppCreator(app, module_name).create()

    def deploy(self, envs: Dict[str, str]):
        """部署 dev sandbox

        :param envs: 启动开发沙箱所需要的环境变量
        """
        sandbox_name = get_dev_sandbox_name(self.dev_wl_app)
        try:
            self.sandbox_mgr.get(self.dev_wl_app, sandbox_name)
        except AppEntityNotFound:
            self._deploy(envs)
        else:
            raise DevSandboxAlreadyExists(f"dev sandbox {sandbox_name} already exists")

    def delete(self):
        """通过直接删除命名空间的方式, 销毁 dev sandbox 服务"""
        ns_handler = NamespacesHandler.new_by_app(self.dev_wl_app)
        ns_handler.delete(namespace=self.dev_wl_app.namespace)

    def get_sandbox_detail(self) -> DevSandboxDetail:
        """获取 dev sandbox 详情"""
        try:
            ingress_entity: DevSandboxIngress = self.ingress_mgr.get(
                self.dev_wl_app, get_ingress_name(self.dev_wl_app)
            )
        except AppEntityNotFound:
            raise DevSandboxResourceNotFound("dev sandbox url not found")

        url = ingress_entity.domains[0].host

        try:
            container_entity: DevSandbox = self.sandbox_mgr.get(self.dev_wl_app, get_dev_sandbox_name(self.dev_wl_app))
        except AppEntityNotFound:
            raise DevSandboxResourceNotFound("dev sandbox not found")

        status = container_entity.status.to_health_phase() if container_entity.status else HealthPhase.UNKNOWN
        return DevSandboxDetail(url=url, envs=container_entity.runtime.envs, status=status)

    def _deploy(self, envs: Dict[str, str]):
        """部署 sandbox 服务"""
        #  step 1. ensure namespace
        ns_handler = NamespacesHandler.new_by_app(self.dev_wl_app)
        ns_handler.ensure_namespace(namespace=self.dev_wl_app.namespace)

        # step 2. create dev sandbox
        default_resources = Resources(
            limits=ResourceSpec(cpu="4", memory="2Gi"),
            requests=ResourceSpec(cpu="200m", memory="512Mi"),
        )

        sandbox_entity = DevSandbox.create(
            self.dev_wl_app,
            runtime=Runtime(envs=envs, image=settings.DEV_SANDBOX_IMAGE),
            resources=default_resources,
        )
        self.sandbox_mgr.create(sandbox_entity)

        # step 3. upsert service
        service_entity = DevSandboxService.create(self.dev_wl_app)
        self.service_mgr.upsert(service_entity)

        # step 4. upsert ingress
        ingress_entity = DevSandboxIngress.create(self.dev_wl_app, self.app.code)
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
        # TODO 考虑更规范的方式处理这两个 cached_property 属性. 如考虑使用 WlAppProtocol 满足 AppEntityManager 模式
        setattr(dev_wl_app, "namespace", f"{DEFAULT_ENGINE_APP_PREFIX}-{self.app.code}-dev".replace("_", "0us0"))
        setattr(dev_wl_app, "module_name", self.module_name)

        return dev_wl_app

    def _make_dev_wl_app_name(self) -> str:
        """参考 make_engine_app_name 规则, 生成 dev 环境的 WlApp name"""
        if self.module_name == ModuleName.DEFAULT.value:
            return f"{DEFAULT_ENGINE_APP_PREFIX}-{self.app.code}-dev"
        else:
            return f"{DEFAULT_ENGINE_APP_PREFIX}-{self.app.code}-m-{self.module_name}-dev"
