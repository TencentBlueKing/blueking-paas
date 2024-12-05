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
from pathlib import Path
from typing import Dict, Optional

from django.conf import settings

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.deploy.app_res.controllers import NamespacesHandler
from paas_wl.bk_app.dev_sandbox.constants import SourceCodeFetchMethod
from paas_wl.bk_app.dev_sandbox.entities import (
    CodeEditorConfig,
    DevSandboxDetail,
    DevSandboxWithCodeEditorDetail,
    DevSandboxWithCodeEditorUrls,
    HealthPhase,
    Resources,
    ResourceSpec,
    Runtime,
    SourceCodeConfig,
)
from paas_wl.bk_app.dev_sandbox.kres_entities import (
    CodeEditor,
    CodeEditorService,
    DevSandbox,
    DevSandboxIngress,
    DevSandboxService,
    get_code_editor_name,
    get_dev_sandbox_name,
    get_ingress_name,
)
from paas_wl.infras.resources.kube_res.base import AppEntityManager
from paas_wl.infras.resources.kube_res.exceptions import AppEntityNotFound
from paas_wl.workloads.volume.persistent_volume_claim.kres_entities import PersistentVolumeClaim, pvc_kmodel
from paasng.platform.applications.models import Application
from paasng.platform.engine.utils.source import upload_source_code
from paasng.platform.modules.constants import DEFAULT_ENGINE_APP_PREFIX, ModuleName
from paasng.platform.sourcectl.models import VersionInfo

from .exceptions import DevSandboxAlreadyExists, DevSandboxResourceNotFound

logger = logging.getLogger(__name__)


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


class DevSandboxWithCodeEditorController:
    """DevSandboxWithCodeEditor Controller,

    区别于 DevSandboxController 它提供了代码编辑器功能以及更方便的部署方式

    :param app: Application 实例
    :param module_name: 模块名称
    :param dev_sandbox_code: 沙盒标识
    :param owner: 沙箱拥有者
    """

    sandbox_mgr: AppEntityManager[DevSandbox] = AppEntityManager[DevSandbox](DevSandbox)
    dev_sandbox_svc_mgr: AppEntityManager[DevSandboxService] = AppEntityManager[DevSandboxService](DevSandboxService)
    ingress_mgr: AppEntityManager[DevSandboxIngress] = AppEntityManager[DevSandboxIngress](DevSandboxIngress)
    code_editor_mgr: AppEntityManager[CodeEditor] = AppEntityManager[CodeEditor](CodeEditor)
    code_editor_svc_mgr: AppEntityManager[CodeEditorService] = AppEntityManager[CodeEditorService](CodeEditorService)

    def __init__(self, app: Application, module_name: str, dev_sandbox_code: str, owner: str):
        self.app = app
        self.module_name = module_name
        self.dev_wl_app: WlApp = _DevWlAppCreator(app, module_name, dev_sandbox_code).create()
        self.dev_sandbox_code = dev_sandbox_code
        self.owner = owner

    def deploy(
        self,
        dev_sandbox_env_vars: Dict[str, str],
        code_editor_env_vars: Dict[str, str],
        version_info: VersionInfo,
        relative_source_dir: Path,
        password: str,
    ):
        """部署 dev sandbox with code editor

        :param dev_sandbox_env_vars: 启动开发沙箱所需要的环境变量
        :param code_editor_env_vars: 启动代码编辑器所需要的环境变量
        :param version_info: 版本信息
        :param relative_source_dir: 代码目录相对路径
        :param password: 部署密码
        """
        sandbox_name = get_dev_sandbox_name(self.dev_wl_app)
        code_editor_name = get_code_editor_name(self.dev_wl_app)

        sandbox_exists = True
        code_editor_exists = True

        try:
            self.sandbox_mgr.get(self.dev_wl_app, sandbox_name)
        except AppEntityNotFound:
            sandbox_exists = False

        try:
            self.code_editor_mgr.get(self.dev_wl_app, code_editor_name)
        except AppEntityNotFound:
            code_editor_exists = False

        if sandbox_exists and code_editor_exists:
            # 如果 sandbox 和 code editor 存在，则不重复创建
            raise DevSandboxAlreadyExists(
                f"dev sandbox {sandbox_name} and code editor {code_editor_name} already exists"
            )
        elif not sandbox_exists and not code_editor_exists:
            # 如果 sandbox 和 code editor 都不存在，则直接部署
            self._deploy(dev_sandbox_env_vars, code_editor_env_vars, version_info, relative_source_dir, password)
        elif sandbox_exists or code_editor_exists:
            # 如果 sandbox, code editor 存在一个，则先删除全部资源再部署
            self.delete()
            self._deploy(dev_sandbox_env_vars, code_editor_env_vars, version_info, relative_source_dir, password)

    def _deploy(
        self,
        dev_sandbox_env_vars: Dict[str, str],
        code_editor_env_vars: Dict[str, str],
        version_info: VersionInfo,
        relative_source_dir: Path,
        password: str,
    ):
        """部署 sandbox 服务"""
        #  step 1. ensure namespace
        ns_handler = NamespacesHandler.new_by_app(self.dev_wl_app)
        ns_handler.ensure_namespace(namespace=self.dev_wl_app.namespace)

        # step 2. create storage
        pvc_kmodel.upsert(
            PersistentVolumeClaim(
                app=self.dev_wl_app,
                name=get_pvc_name(self.dev_wl_app),
                storage="1Gi",
                storage_class_name=settings.DEFAULT_PERSISTENT_STORAGE_CLASS_NAME,
            )
        )

        # step 3. create dev sandbox
        self._create_dev_sandbox(dev_sandbox_env_vars, version_info, relative_source_dir)

        # step 4. create code editor
        self._create_code_editor(code_editor_env_vars, password)

        # step 5. upsert service
        dev_sandbox_svc_entity = DevSandboxService.create(self.dev_wl_app)
        self.dev_sandbox_svc_mgr.upsert(dev_sandbox_svc_entity)
        code_editor_svc_entity = CodeEditorService.create(self.dev_wl_app)
        self.code_editor_svc_mgr.upsert(code_editor_svc_entity)

        # step 6. upsert ingress
        ingress_entity = DevSandboxIngress.create(self.dev_wl_app, self.app.code, self.dev_sandbox_code)
        self.ingress_mgr.upsert(ingress_entity)

    def _create_dev_sandbox(
        self, dev_sandbox_env_vars: Dict[str, str], version_info: VersionInfo, relative_source_dir: Path
    ):
        # upload source code
        module = self.app.get_module(self.module_name)
        source_fetch_url = upload_source_code(
            module, version_info, relative_source_dir, self.owner, self.dev_wl_app.region
        )

        # create dev sandbox
        default_sandbox_resources = Resources(
            limits=ResourceSpec(cpu="4", memory="2Gi"),
            requests=ResourceSpec(cpu="200m", memory="512Mi"),
        )

        source_code_config = SourceCodeConfig(
            pvc_claim_name=get_pvc_name(self.dev_wl_app),
            workspace=settings.DEV_SANDBOX_WORKSPACE,
            source_fetch_url=source_fetch_url,
            source_fetch_method=SourceCodeFetchMethod.BK_REPO,
        )

        sandbox_entity = DevSandbox.create(
            self.dev_wl_app,
            runtime=Runtime(envs=dev_sandbox_env_vars, image=settings.DEV_SANDBOX_IMAGE),
            resources=default_sandbox_resources,
            source_code_config=source_code_config,
        )
        sandbox_entity.construct_envs()
        self.sandbox_mgr.create(sandbox_entity)

    def _create_code_editor(self, code_editor_env_vars: Dict[str, str], password: str):
        default_code_editor_resources = Resources(
            limits=ResourceSpec(cpu="4", memory="2Gi"),
            requests=ResourceSpec(cpu="500m", memory="1024Mi"),
        )

        code_editor_config = CodeEditorConfig(
            pvc_claim_name=get_pvc_name(self.dev_wl_app), start_dir=settings.CODE_EDITOR_START_DIR, password=password
        )

        code_editor_entity = CodeEditor.create(
            self.dev_wl_app,
            runtime=Runtime(envs=code_editor_env_vars, image=settings.CODE_EDITOR_IMAGE),
            resources=default_code_editor_resources,
            config=code_editor_config,
        )
        code_editor_entity.construct_envs()
        self.code_editor_mgr.create(code_editor_entity)

    def delete(self):
        """通过直接删除命名空间的方式, 销毁 dev sandbox 服务"""
        ns_handler = NamespacesHandler.new_by_app(self.dev_wl_app)
        ns_handler.delete(namespace=self.dev_wl_app.namespace)

    def _get_url(self) -> str:
        """获取 dev sandbox url"""
        try:
            ingress_entity: DevSandboxIngress = self.ingress_mgr.get(
                self.dev_wl_app, get_ingress_name(self.dev_wl_app)
            )
        except AppEntityNotFound:
            raise DevSandboxResourceNotFound("dev sandbox url not found")

        return ingress_entity.domains[0].host

    def get_detail(self) -> DevSandboxWithCodeEditorDetail:
        """
        获取详情
        raises: DevSandboxResourceNotFound: 如果开发沙箱资源（dev_sandbox 或者 code_editor）未找到。
        """
        try:
            dev_sandbox_entity: DevSandbox = self.sandbox_mgr.get(
                self.dev_wl_app, get_dev_sandbox_name(self.dev_wl_app)
            )
        except AppEntityNotFound:
            raise DevSandboxResourceNotFound("dev sandbox not found")

        try:
            code_editor_entity: CodeEditor = self.code_editor_mgr.get(
                self.dev_wl_app, get_code_editor_name(self.dev_wl_app)
            )
        except AppEntityNotFound:
            raise DevSandboxResourceNotFound("code editor not found")

        base_url = self._get_url()
        urls = DevSandboxWithCodeEditorUrls(base_url=base_url, dev_sandbox_code=self.dev_sandbox_code)

        dev_sandbox_status = (
            dev_sandbox_entity.status.to_health_phase() if dev_sandbox_entity.status else HealthPhase.UNKNOWN
        )
        code_editor_status = (
            code_editor_entity.status.to_health_phase() if code_editor_entity.status else HealthPhase.UNKNOWN
        )
        return DevSandboxWithCodeEditorDetail(
            dev_sandbox_env_vars=dev_sandbox_entity.runtime.envs,
            code_editor_env_vars=code_editor_entity.runtime.envs,
            dev_sandbox_status=dev_sandbox_status,
            code_editor_status=code_editor_status,
            urls=urls,
        )


class _DevWlAppCreator:
    """WlApp 实例构造器

    :param app: 应用
    :param module_name: 模块名称
    :param dev_sandbox_code: 沙箱标识，在模块下沙箱不唯一时传入
    """

    def __init__(self, app: Application, module_name: str, dev_sandbox_code: Optional[str] = None):
        self.app = app
        self.module_name = module_name
        self.dev_sandbox_code = dev_sandbox_code

    def create(self) -> WlApp:
        """创建 WlApp 实例"""
        dev_wl_app = WlApp(region=self.app.region, name=self._make_dev_wl_app_name(), type=self.app.type)

        # 因为 dev_wl_app 不是查询集结果, 所以需要覆盖 namespace 和 module_name, 以保证 AppEntityManager 模式能够正常工作
        # TODO 考虑更规范的方式处理这两个 cached_property 属性. 如考虑使用 WlAppProtocol 满足 AppEntityManager 模式
        namespace_name = self._make_namespace_name()
        setattr(dev_wl_app, "namespace", namespace_name.replace("_", "0us0"))
        setattr(dev_wl_app, "module_name", self.module_name)

        return dev_wl_app

    def _make_dev_wl_app_name(self) -> str:
        """参考 make_engine_app_name 规则, 生成 dev 环境的 WlApp name"""
        suffix = f"{self.dev_sandbox_code}-dev" if self.dev_sandbox_code else "dev"

        if self.module_name == ModuleName.DEFAULT.value:
            return f"{DEFAULT_ENGINE_APP_PREFIX}-{self.app.code}-{suffix}"

        return f"{DEFAULT_ENGINE_APP_PREFIX}-{self.app.code}-m-{self.module_name}-{suffix}"

    def _make_namespace_name(self) -> str:
        """生成 namespace_name"""
        ns = f"{DEFAULT_ENGINE_APP_PREFIX}-{self.app.code}-dev"
        if self.dev_sandbox_code:
            ns = f"{ns}-{self.dev_sandbox_code}"

        return ns


def get_pvc_name(dev_wl_app: WlApp) -> str:
    return f"{dev_wl_app.scheduler_safe_name}-pvc"
