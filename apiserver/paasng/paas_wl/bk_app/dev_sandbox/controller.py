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

from attr import define, field

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.deploy.app_res.controllers import NamespacesHandler
from paas_wl.bk_app.dev_sandbox.conf import (
    APP_SERVER_NETWORK_CONFIG,
    CODE_EDITOR_NETWORK_CONFIG,
    DEV_SANDBOX_WORKSPACE,
    DEV_SERVER_NETWORK_CONFIG,
)
from paas_wl.bk_app.dev_sandbox.entities import CodeEditorConfig, Runtime, SourceCodeConfig
from paas_wl.bk_app.dev_sandbox.exceptions import DevSandboxAlreadyExists, DevSandboxResourceNotFound
from paas_wl.bk_app.dev_sandbox.kres_entities import (
    DevSandbox,
    DevSandboxConfigMap,
    DevSandboxIngress,
    DevSandboxService,
)
from paas_wl.bk_app.dev_sandbox.names import get_dev_sandbox_ingress_name, get_dev_sandbox_name
from paas_wl.infras.resources.kube_res.base import AppEntityManager
from paas_wl.infras.resources.kube_res.exceptions import AppEntityNotFound
from paasng.platform.applications.constants import AppEnvironment
from paasng.platform.modules.constants import DEFAULT_ENGINE_APP_PREFIX, ModuleName

if TYPE_CHECKING:
    from paasng.accessories.dev_sandbox.models import DevSandbox as DevSandboxModel

logger = logging.getLogger(__name__)


@define
class DevSandboxUrls:
    """沙箱服务访问地址"""

    base: str
    app: str = field(init=False)
    devserver: str = field(init=False)
    code_editor: str = field(init=False)

    def __attrs_post_init__(self):
        self.app = f"{self.base}{APP_SERVER_NETWORK_CONFIG.path_prefix}"
        self.devserver = f"{self.base}{DEV_SERVER_NETWORK_CONFIG.path_prefix}"
        self.code_editor = f"{self.base}{CODE_EDITOR_NETWORK_CONFIG.path_prefix}"


@define
class DevSandboxDetail:
    """沙箱服务详情"""

    workspace: str
    urls: DevSandboxUrls
    envs: Dict[str, str]
    status: str


class DevSandboxController:
    """开发沙箱控制器

    :param dev_sandbox: 开发沙箱（DB 模型）
    """

    sandbox_mgr = AppEntityManager(DevSandbox)
    service_mgr = AppEntityManager(DevSandboxService)
    ingress_mgr = AppEntityManager(DevSandboxIngress)
    configmap_mgr = AppEntityManager(DevSandboxConfigMap)

    def __init__(self, dev_sandbox: "DevSandboxModel"):
        self.dev_sandbox = dev_sandbox
        self.wl_app: WlApp = DevWlAppConstructor(dev_sandbox).construct()

    def deploy(
        self,
        envs: Dict[str, str],
        source_code_cfg: SourceCodeConfig,
        code_editor_cfg: CodeEditorConfig | None = None,
    ):
        """部署开发沙箱

        :param envs: 启动开发沙箱所需要的环境变量
        :param source_code_cfg: 源码配置
        :param code_editor_cfg: 代码编辑器配置
        """
        sandbox_name = get_dev_sandbox_name(self.wl_app)
        try:
            self.sandbox_mgr.get(self.wl_app, sandbox_name)
        except AppEntityNotFound:
            self._deploy(envs, source_code_cfg, code_editor_cfg)
        else:
            raise DevSandboxAlreadyExists(f"dev sandbox {sandbox_name} already exists")

    def delete(self):
        """通过直接删除命名空间的方式, 销毁 dev sandbox 服务"""
        ns_handler = NamespacesHandler.new_by_app(self.wl_app)
        ns_handler.delete(namespace=self.wl_app.namespace)

    def get_detail(self) -> DevSandboxDetail:
        """获取 dev sandbox 详情"""
        try:
            ingress_name = get_dev_sandbox_ingress_name(self.wl_app)
            ingress: DevSandboxIngress = self.ingress_mgr.get(self.wl_app, ingress_name)
        except AppEntityNotFound:
            raise DevSandboxResourceNotFound("dev sandbox ingress not found")

        base_url = f"{ingress.domains[0].host}/dev_sandbox/{self.dev_sandbox.code}"

        try:
            dev_sandbox_name = get_dev_sandbox_name(self.wl_app)
            dev_sandbox: DevSandbox = self.sandbox_mgr.get(self.wl_app, dev_sandbox_name)
        except AppEntityNotFound:
            raise DevSandboxResourceNotFound("dev sandbox not found")

        return DevSandboxDetail(
            workspace=DEV_SANDBOX_WORKSPACE,
            urls=DevSandboxUrls(base=base_url),
            envs=dev_sandbox.runtime.envs,
            status=dev_sandbox.status,
        )

    def _deploy(
        self,
        envs: Dict[str, str],
        source_code_cfg: SourceCodeConfig,
        code_editor_cfg: CodeEditorConfig | None = None,
    ):
        """部署 sandbox 服务"""
        #  step 1. ensure namespace
        ns_handler = NamespacesHandler.new_by_app(self.wl_app)
        ns_handler.ensure_namespace(namespace=self.wl_app.namespace)

        # step 2. create dev sandbox
        sandbox = DevSandbox.create(
            self.wl_app,
            code=self.dev_sandbox.code,
            token=self.dev_sandbox.token,
            runtime=Runtime(envs=envs),
            source_code_cfg=source_code_cfg,
            code_editor_cfg=code_editor_cfg,
        )

        # step 3. create configmap
        cfg_map = DevSandboxConfigMap.create(sandbox)
        # deliver code-editor config via ConfigMap
        self.configmap_mgr.upsert(cfg_map)

        # 创建沙箱 pod
        self.sandbox_mgr.create(sandbox)

        # step 4. upsert service
        self.service_mgr.upsert(DevSandboxService.create(sandbox))

        # step 5. upsert ingress
        self.ingress_mgr.upsert(DevSandboxIngress.create(sandbox))


class DevWlAppConstructor:
    """开发沙箱用 WlApp 实例构造器"""

    def __init__(self, dev_sandbox: "DevSandboxModel"):
        self.dev_sandbox = dev_sandbox
        self.module = dev_sandbox.module
        self.app = self.module.application

    def construct(self) -> WlApp:
        """构造 WlApp 实例（非 DB 数据）"""
        dev_wl_app = WlApp(
            region=self.app.region,
            tenant_id=self.app.tenant_id,
            name=self._make_dev_wl_app_name(),
            type=self.app.type,
        )

        # 因为 dev_wl_app 不是查询集结果, 所以需要覆盖 namespace 和 module_name, 以保证 AppEntityManager 模式能够正常工作
        # TODO 考虑更规范的方式处理这两个 cached_property 属性. 如考虑使用 WlAppProtocol 满足 AppEntityManager 模式
        setattr(dev_wl_app, "namespace", self._make_namespace_name())
        setattr(dev_wl_app, "module_name", self.module.name)
        setattr(dev_wl_app, "paas_app_code", self.app.code)
        setattr(dev_wl_app, "environment", AppEnvironment.STAGING)

        return dev_wl_app

    def _make_dev_wl_app_name(self) -> str:
        """参考 make_engine_app_name 规则, 生成 dev 环境的 WlApp name"""
        suffix = f"{self.dev_sandbox.code}-dev" if self.dev_sandbox.code else "dev"

        if self.module.name == ModuleName.DEFAULT.value:
            return f"{DEFAULT_ENGINE_APP_PREFIX}-{self.app.code}-{suffix}"

        return f"{DEFAULT_ENGINE_APP_PREFIX}-{self.app.code}-m-{self.module.name}-{suffix}"

    def _make_namespace_name(self) -> str:
        """生成 namespace_name"""
        ns = f"{DEFAULT_ENGINE_APP_PREFIX}-{self.app.code}-dev"
        if self.dev_sandbox.code:
            ns = f"{ns}-{self.dev_sandbox.code}"

        return ns.replace("_", "0us0")
