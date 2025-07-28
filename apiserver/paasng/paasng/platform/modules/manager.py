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

"""Management functions for application module, may include:

- Module initialization
- Module deletion / recycle
"""

import logging
from contextlib import contextmanager
from operator import attrgetter
from typing import Any, Dict, List, Optional

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils.translation import gettext as _

from paas_wl.bk_app.applications.api import create_app_ignore_duplicated, update_metadata_by_env
from paas_wl.bk_app.applications.constants import WlAppType
from paas_wl.bk_app.deploy.actions.delete import delete_module_related_res
from paas_wl.infras.cluster.shim import EnvClusterService, get_exposed_url_type
from paasng.accessories.servicehub.exceptions import ServiceObjNotFound
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.sharing import SharingReferencesManager
from paasng.platform.applications.constants import AppEnvironment, ApplicationType
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.bkapp_model.entities import Monitoring, Process
from paasng.platform.bkapp_model.entities_syncer import sync_processes
from paasng.platform.bkapp_model.fieldmgr.constants import FieldMgrName
from paasng.platform.bkapp_model.models import ObservabilityConfig, ProcessSpecEnvOverlay
from paasng.platform.engine.constants import RuntimeType
from paasng.platform.engine.models import EngineApp
from paasng.platform.modules import entities
from paasng.platform.modules.constants import DEFAULT_ENGINE_APP_PREFIX, ModuleName, SourceOrigin
from paasng.platform.modules.entities import ModuleInitResult, VcsInitResult
from paasng.platform.modules.exceptions import ModuleInitializationError
from paasng.platform.modules.handlers import on_module_initialized
from paasng.platform.modules.helpers import (
    ModuleRuntimeBinder,
    get_image_labels_by_module,
    update_build_config_with_method,
)
from paasng.platform.modules.models import AppSlugBuilder, AppSlugRunner, BuildConfig, Module
from paasng.platform.modules.models.build_cfg import ImageTagOptions
from paasng.platform.modules.specs import ModuleSpecs
from paasng.platform.modules.utils import get_module_init_repo_context
from paasng.platform.sourcectl.connector import get_repo_connector
from paasng.platform.sourcectl.docker.models import init_image_repo
from paasng.platform.sourcectl.source_types import get_sourcectl_type
from paasng.platform.templates.constants import TemplateType
from paasng.platform.templates.manager import AppBuildPack, TemplateRuntimeManager
from paasng.platform.templates.models import Template
from paasng.platform.templates.templater import generate_initial_code, upload_directory_to_storage
from paasng.utils.addons import ReplaceableFunction
from paasng.utils.basic import get_username_by_bkpaas_user_id
from paasng.utils.dictx import get_items
from paasng.utils.error_codes import error_codes

logger = logging.getLogger(__name__)
make_app_metadata = ReplaceableFunction(default_factory=dict)


class ModuleBuildpackPlaner:
    """ModuleBuildpackPlaner 的职责是协助 ModuleInitializer 初始化运行时需要的构建工具

    ModuleBuildpackPlaner 与 TemplateRuntimeManager 的行为类似但不一样:
    - ModuleBuildpackPlaner 关注的是 module, 而 TemplateRuntimeManager 关注的是 template
    - 处理从模板创建的 Module 时, ModuleBuildpackPlaner 与 TemplateRuntimeManager **完全**一致
    - 由于并非所有 Module 都从模板创建, 因此目前并不能用 TemplateRuntimeManager 取代 ModuleBuildpackPlaner, 涉及的应用类型:
        - BK_LESSCODE
        - BK_PLUGINS
    """

    def __init__(self, module: Module):
        self.module = module

    def get_required_buildpacks(self, bp_stack_name: str) -> List[AppBuildPack]:
        """获取构建模板代码需要的构建工具"""
        try:
            required_buildpacks = TemplateRuntimeManager(
                self.module.source_init_template
            ).get_template_required_buildpacks(bp_stack_name=bp_stack_name)
        except Template.DoesNotExist:
            required_buildpacks = []

        language_bp = self.get_language_buildpack(bp_stack_name=bp_stack_name)
        if language_bp:
            required_buildpacks.append(language_bp)
        return required_buildpacks

    def get_language_buildpack(self, bp_stack_name: str) -> Optional[AppBuildPack]:
        """获取和模块语言相关的构建工具"""
        builder = AppSlugBuilder.objects.get(name=bp_stack_name)
        buildpacks = builder.get_buildpack_choices(self.module, language=self.module.language)
        if not buildpacks:
            return None
        # 选取指定语言的最新一个非隐藏的 buildpack
        buildpack = sorted(buildpacks, key=attrgetter("created"))[-1]
        return buildpack


class ModuleInitializer:
    """Initializer for Module"""

    default_environments = ["stag", "prod"]

    def __init__(self, module: Module):
        self.module = module
        self.application = self.module.application

    def make_engine_app_name(self, env: str) -> str:
        return make_engine_app_name(self.module, self.application.code, env)

    def make_engine_meta_info(self, env: ModuleEnvironment) -> Dict[str, Any]:
        ext_metadata = make_app_metadata(env)
        return {
            "paas_app_code": self.application.code,
            "module_name": self.module.name,
            "environment": env.environment,
            **ext_metadata,
        }

    @transaction.atomic
    def create_engine_apps(self, env_cluster_names: Dict[str, str] | None = None):
        """Create engine app instances for application"""
        env_cluster_names = env_cluster_names if env_cluster_names else {}

        wl_app_type = (
            WlAppType.CLOUD_NATIVE if self.application.type == ApplicationType.CLOUD_NATIVE else WlAppType.DEFAULT
        )

        for environment in self.default_environments:
            name = self.make_engine_app_name(environment)
            engine_app = self._get_or_create_engine_app(name, wl_app_type)
            env = ModuleEnvironment.objects.create(
                application=self.application,
                module=self.module,
                engine_app_id=engine_app.id,
                environment=environment,
                tenant_id=self.application.tenant_id,
            )
            # 为部署环境绑定集群，支持以模块创建者的身份选择可用集群
            username = get_username_by_bkpaas_user_id(self.module.creator)
            EnvClusterService(env).bind_cluster(env_cluster_names.get(environment), operator=username)

            # Update metadata
            engine_app_meta_info = self.make_engine_meta_info(env)
            update_metadata_by_env(env, engine_app_meta_info)

        # Also set the module's exposed_url_type by the cluster
        self.module.exposed_url_type = get_exposed_url_type(
            application=self.application, cluster_name=env_cluster_names.get(AppEnvironment.PRODUCTION)
        ).value
        self.module.save(update_fields=["exposed_url_type"])

    def initialize_vcs_with_template(
        self,
        repo_type: Optional[str] = None,
        repo_url: Optional[str] = None,
        repo_auth_info: Optional[dict] = None,
        source_dir: str = "",
        write_template_to_repo: bool = False,
    ) -> VcsInitResult:
        """Initialize module vcs with source template

        :param repo_type: the type of repository provider, used when source_origin is `AUTHORIZED_VCS`
        :param repo_url: the address of repository, used when source_origin is `AUTHORIZED_VCS`
        :param repo_auth_info: the auth of repository
        :param source_dir: The work dir, which containing Procfile.
        :param write_template_to_repo: whether to initialize template to repo
        """
        if not self._should_initialize_vcs():
            logger.info(
                "Skip initializing template for application:<%s>/<%s>", self.application.code, self.module.name
            )
            return VcsInitResult(code="OK")

        if not repo_type:
            raise ValueError("repo type must not be None")

        # 将代码仓库地址等信息存储到 model 字段中
        connector = get_repo_connector(repo_type, self.module)
        connector.bind(repo_url, source_dir=source_dir, repo_auth_info=repo_auth_info)

        result = VcsInitResult(code="OK")
        # # Only run syncing procedure when `source_init_template` is valid
        try:
            template = Template.objects.get(name=self.module.source_init_template)
        except Template.DoesNotExist:
            return result

        # 插件模板，且不需要初始化代码，则不需要下载模板代码直接返回
        if template.type == TemplateType.PLUGIN and not write_template_to_repo:
            return result

        # 下载并渲染模板代码到本地目录
        context = get_module_init_repo_context(self.module, template.type)
        initial_code_path = generate_initial_code(template.name, context)

        # 将普通模板的初始化代码上传到对象存储
        if template.type == TemplateType.NORMAL:
            syc_res = upload_directory_to_storage(self.module, initial_code_path)
            if syc_res.is_success():
                result = VcsInitResult(code="OK", extra_info=syc_res.extra_info, dest_type=syc_res.dest_type)
            else:
                result = VcsInitResult(code=syc_res.error, error=syc_res.error)

        # 将模板代码初始化到应用的代码仓库中
        if write_template_to_repo and repo_url:
            source_type = get_sourcectl_type(self.module.source_type)
            repo_controller = source_type.repo_controller_class.init_by_module(self.module, self.module.owner)
            repo_controller.commit_and_push(initial_code_path, commit_message="init repo")

        # 返回应用初始化代码同步到对象存储的地址信息，用于前端创建成功页面的展示
        return result

    def _should_initialize_vcs(self) -> bool:
        """Check if current module should run source template initializing procedure"""
        module_specs = ModuleSpecs(self.module)
        # Matches app type: ENGINELESS_APP
        if not module_specs.app_specs.engine_enabled:
            return False

        # Matches source_origin type: S-Mart App or Lesscode
        if module_specs.source_origin_specs.deploy_via_package:
            return False

        # Matches source origin type: IMAGE_REGISTRY or CNATIVE_IMAGE
        return module_specs.runtime_type != RuntimeType.CUSTOM_IMAGE

    def bind_default_services(self):
        """Bind default services after module creation"""
        DefaultServicesBinder(self.module).bind()

    def initialize_docker_build_config(self, cfg: entities.BuildConfig):
        """初始化 Dockerfile 类型的构建配置

        :param cfg: 构建配置, 其中含有 Dockerfile 相关的构建参数等
        """
        db_instance = BuildConfig.objects.get_or_create_by_module(self.module)
        update_build_config_with_method(
            db_instance,
            build_method=cfg.build_method,
            data={"dockerfile_path": cfg.dockerfile_path, "docker_build_args": cfg.docker_build_args or {}},
        )

    def bind_default_runtime(self):
        """Bind slugbuilder/slugrunner/buildpacks after module creation"""
        runtime_labels = get_image_labels_by_module(self.module)
        self.bind_runtime_by_labels(runtime_labels)

    def bind_runtime_by_labels(self, labels: Dict[str, str], contain_hidden: bool = False):
        """Bind slugbuilder/slugrunner/buildpacks by labels"""
        try:
            slugbuilder = AppSlugBuilder.objects.select_default_runtime(labels, contain_hidden)
            # by designed, name must be consistent between builder and runner
            slugrunner = AppSlugRunner.objects.get(name=slugbuilder.name)
        except ObjectDoesNotExist:
            # 找不到则使用 app engine 默认配置的镜像
            logger.warning("skip runtime binding because default image is not found")
            return

        binder = ModuleRuntimeBinder(self.module)
        binder.bind_image(slugrunner, slugbuilder)

        planer = ModuleBuildpackPlaner(module=self.module)
        for buildpack in planer.get_required_buildpacks(bp_stack_name=slugbuilder.name):
            binder.bind_buildpack(buildpack)

    def initialize_app_model_resource(self, bkapp_spec: Dict[str, Any]):
        """
        Initialize the AppModelResource and import the bkapp_spec into the corresponding bkapp models

        :param bkapp_spec: validated_data from CreateBkAppSpecSLZ
        """
        # 只有云原生应用需要在创建模块后初始化 AppModelResource
        if self.application.type != ApplicationType.CLOUD_NATIVE:
            return

        if not bkapp_spec or bkapp_spec["build_config"].build_method != RuntimeType.CUSTOM_IMAGE:
            return

        # 镜像交付的应用需要将模块配置导入到 DB(bkapp model)
        # 导入 BuildConfig
        build_config = bkapp_spec["build_config"]
        config_obj = BuildConfig.objects.get_or_create_by_module(self.module)
        build_params = {
            "image_repository": build_config.image_repository,
            "image_credential_name": None,
        }
        if image_credential := build_config.image_credential:
            build_params["image_credential_name"] = image_credential["name"]
        update_build_config_with_method(config_obj, build_method=build_config.build_method, data=build_params)

        processes = [
            Process(
                name=proc_spec["name"],
                command=proc_spec["command"],
                args=proc_spec["args"],
                target_port=proc_spec.get("port", None),
                probes=proc_spec.get("probes", None),
                services=proc_spec.get("services", None),
            )
            for proc_spec in bkapp_spec["processes"]
        ]

        sync_processes(self.module, processes, manager=FieldMgrName.WEB_FORM)

        # 更新环境覆盖&更新可观测功能配置
        metrics = []
        for proc_spec in bkapp_spec["processes"]:
            if env_overlay := proc_spec.get("env_overlay"):
                for env_name, proc_env_overlay in env_overlay.items():
                    ProcessSpecEnvOverlay.objects.save_by_module(
                        self.module, proc_spec["name"], env_name, **proc_env_overlay
                    )

            if metric := get_items(proc_spec, ["monitoring", "metric"]):
                metrics.append({"process": proc_spec["name"], **metric})

        monitoring = Monitoring(metrics=metrics) if metrics else None
        ObservabilityConfig.objects.upsert_by_module(self.module, monitoring)

        # 导入 hook 配置
        if hook := bkapp_spec.get("hook"):
            self.module.deploy_hooks.enable_hook(
                type_=hook["type"],
                proc_command=hook.get("proc_command"),
                command=hook.get("command"),
                args=hook.get("args"),
            )

    def _get_or_create_engine_app(self, name: str, app_type: WlAppType) -> EngineApp:
        """Create or get existed engine app by given name"""
        info = create_app_ignore_duplicated(self.application.region, name, app_type, self.application.tenant_id)
        engine_app = EngineApp.objects.create(
            id=info.uuid,
            name=info.name,
            owner=self.application.owner,
            region=self.application.region,
            tenant_id=self.application.tenant_id,
        )
        return engine_app


@contextmanager
def _humanize_exception(step_name: str, message: str):
    """Transform all exception when initialize module into ModuleInitializationError with human friendly message"""
    try:
        yield
    except Exception as e:
        logger.exception("An exception occurred during `%s`", step_name)
        raise ModuleInitializationError(message) from e


def create_repo_with_platform_account(module: Module, repo_type: str, username: str) -> str:
    """使用平台账号创建代码仓库（提供给插件应用使用）

    :param module: 需要创建仓库的模块对象
    :param username: 需要添加为仓库成员的初始用户名
    :param repo_type: 代码仓库类型
    :return: 新创建的代码仓库地址
    """
    source_type = get_sourcectl_type(repo_type)
    source_type_config = source_type.config_as_arguments()

    if "repo_group" not in source_type_config:
        logger.error("repo_group is not found in source type config")
        raise error_codes.CANNOT_CREATE_APP.f(_("平台代码仓库组配置缺失"))

    if not source_type.repo_provisioner_class:
        raise error_codes.CANNOT_CREATE_APP.f(_("当前代码源不支持新建仓库"))

    repo_group = source_type_config["repository_group"]
    repo_name = f"{module.application.code}_{module.name}"
    repo_provisioner = source_type.repo_provisioner_class.init_by_platform_account(repo_type)

    return repo_provisioner.create_with_member(
        repo_name=repo_name,
        description=f"{module.application.name}({module.name} 模块)",
        username=username,
        repo_group=repo_group,
    )


def create_repo_with_user_account(
    module: Module,
    repo_type: str,
    repo_name: str,
    username: str,
    repo_group: str | None = None,
) -> str:
    """使用用户凭证创建仓库

    :param module: 需要创建仓库的模块对象
    :param repo_type: 代码仓库类型
    :param repo_name: 代码仓库名称
    :param username: 需要添加为仓库成员的初始用户名
    :param repo_group: 代码仓库组，可选，不填则默认在用户命名空间下创建
    :return: 新创建的代码仓库地址
    """
    source_type = get_sourcectl_type(repo_type)
    if not source_type.repo_provisioner_class:
        raise error_codes.CANNOT_CREATE_APP.f(_("当前代码源不支持新建仓库"))

    repo_provisioner = source_type.repo_provisioner_class.init_by_user(repo_type, user_id=module.owner)

    return repo_provisioner.create_with_member(
        repo_name=repo_name,
        description=f"{module.application.name}({module.name} 模块)",
        username=username,
        repo_group=repo_group,
    )


def delete_repo(repo_type: str, repo_url: str, user_id: str):
    """Delete the code repository created by the platform

    :param repo_type: 仓库类型
    :param repo_url: 仓库地址
    :param user_id: 用户 ID，用于查询用户对应的授权凭证
    """
    source_type = get_sourcectl_type(repo_type)
    if not source_type.repo_provisioner_class:
        raise error_codes.CANNOT_CREATE_APP.f(_("当前代码源不支持删除仓库"))

    repo_provisioner = source_type.repo_provisioner_class.init_by_user(repo_type, user_id)
    repo_provisioner.delete_project(repo_url)


@contextmanager
def delete_repo_on_error(user_id: str, repo_type: str, repo_url: str | None = None):
    """仓库清理上下文管理器，在异常时自动删除新建的仓库

    :param user_id: 用户 ID，用于查询用户对应的授权凭证
    :param repo_type: 仓库类型
    :param repo_url: 仓库地址（可选），用于判断是否需要删除代码仓库
    """
    try:
        yield
    except Exception:
        if repo_url:
            try:
                delete_repo(repo_type, repo_url, user_id)
                logger.info(f"Repository({repo_url}) deleted successfully  during rollback")
            except Exception:
                logger.exception(f"Failed to delete repository({repo_url}) during rollback")
        raise


def init_module_in_view(*args, **kwargs) -> ModuleInitResult:
    """Initialize a module in view function, see `initialize_module(...)` for more information

    :raises: APIError when any error occurs
    """
    try:
        return initialize_module(*args, **kwargs)
    except ModuleInitializationError as e:
        raise error_codes.CANNOT_CREATE_APP.f(str(e))


def initialize_smart_module(module: Module, env_cluster_names: Dict[str, str]):
    """Initialize a module for s-mart app"""
    module_initializer = ModuleInitializer(module)
    module_spec = ModuleSpecs(module)

    # Create engine apps first
    with _humanize_exception("create_engine_apps", _("服务暂时不可用，请稍候再试")):
        module_initializer.create_engine_apps(env_cluster_names=env_cluster_names)

    with _humanize_exception("bind_default_services", _("绑定初始增强服务失败，请稍候再试")):
        module_initializer.bind_default_services()

    if module_spec.runtime_type == RuntimeType.BUILDPACK:
        # bind heroku runtime, such as slug builder/runner and buildpacks
        with _humanize_exception(_("绑定初始运行环境失败，请稍候再试"), "bind default runtime"):
            module_initializer.bind_default_runtime()

    on_module_initialized.send(sender=initialize_smart_module, module=module)
    return ModuleInitResult(source_init_result=VcsInitResult(code="OK"))


def initialize_module(
    module: Module,
    repo_type: str,
    repo_url: Optional[str],
    repo_auth_info: Optional[dict],
    env_cluster_names: Dict[str, str],
    source_dir: str = "",
    bkapp_spec: Optional[Dict] = None,
    write_template_to_repo: bool = False,
) -> ModuleInitResult:
    """Initialize a module

    :param repo_type: sourcectl type name, see SourceTypeSpecConfig table data for all names
    :param repo_url: The address of repository, such as "git://x.git.com/repo"
    :param repo_auth_info: The auth of repository, such as {"username": "ddd", "password": "www"}
    :param source_dir: The work dir, which containing Procfile.
    :param cluster_name: optional engine cluster name
    :param bkapp_spec: optional cnative module bkapp_spec
    :param write_template_to_repo: whether to initialize template to repo
    :raises: ModuleInitializationError when any steps failed
    """
    module_initializer = ModuleInitializer(module)
    module_spec = ModuleSpecs(module)

    # Create engine apps first
    with _humanize_exception("create_engine_apps", _("服务暂时不可用，请稍候再试")):
        module_initializer.create_engine_apps(env_cluster_names=env_cluster_names)

    source_init_result = VcsInitResult(code="OK")
    if module_spec.has_vcs:
        # initialize module vcs with template if required
        with _humanize_exception("initialize_app_source", _("代码初始化过程失败，请稍候再试")):
            source_init_result = module_initializer.initialize_vcs_with_template(
                repo_type,
                repo_url,
                repo_auth_info=repo_auth_info,
                source_dir=source_dir,
                write_template_to_repo=write_template_to_repo,
            )

    build_config = bkapp_spec["build_config"] if bkapp_spec else None
    if not build_config:
        if module_spec.templated_source_enabled:
            tmpl_mgr = TemplateRuntimeManager(tmpl_name=module.source_init_template)
            build_config = entities.BuildConfig(
                build_method=tmpl_mgr.template.runtime_type, tag_options=ImageTagOptions()
            )
        else:
            build_config = entities.BuildConfig(build_method=module_spec.runtime_type, tag_options=ImageTagOptions())

    config_obj = BuildConfig.objects.get_or_create_by_module(module)
    config_obj.build_method = build_config.build_method
    config_obj.save(update_fields=["build_method"])

    if build_config.build_method == RuntimeType.BUILDPACK:
        with _humanize_exception("bind_default_runtime", _("绑定初始运行环境失败，请稍候再试")):
            # bind heroku runtime, such as slug builder/runner and buildpacks
            module_initializer.bind_default_runtime()
    elif build_config.build_method == RuntimeType.DOCKERFILE:
        with _humanize_exception("bind_default_runtime", _("绑定初始运行环境失败，请稍候再试")):
            module_initializer.initialize_docker_build_config(build_config)
    elif module_spec.source_origin == SourceOrigin.IMAGE_REGISTRY:
        with _humanize_exception("config_image_registry", _("配置镜像 Registry 失败，请稍候再试")):
            init_image_repo(module, repo_url or "", source_dir, repo_auth_info or {})

    with _humanize_exception("bind_default_services", _("绑定初始增强服务失败，请稍候再试")):
        module_initializer.bind_default_services()

    if bkapp_spec:
        with _humanize_exception("initialize_app_model_resource", _("初始化应用模型失败, 请稍候再试")):
            module_initializer.initialize_app_model_resource(bkapp_spec)

    on_module_initialized.send(sender=initialize_module, module=module)
    return ModuleInitResult(source_init_result=source_init_result)


class ModuleCleaner:
    def __init__(self, module: Module):
        self.module = module

    def clean(self):
        """main entrance to clean module"""
        logger.info("going to delete services related to Module<%s>", self.module)
        self.delete_services()

        logger.info("going to delete EngineApp related to Module<%s>", self.module)
        self.delete_engine_apps()

        # 数据记录删除(module 是真删除)
        logger.info("going to delete Module<%s>", self.module)
        self.delete_module()

    def delete_services(self, service_id: Optional[str] = None):
        """删除所有关联增强服务，以及所有被其他模块共享引用的服务关系

        :param service_id: 需要删除的服务 UUID，当值为 None 时，删除所有 module 关联增强服务
        """
        services = []
        for env in self.module.get_envs():
            # 这里拿到的是 EngineAppAttachment
            relations = mixed_service_mgr.list_all_rels(engine_app=env.engine_app, service_id=service_id)
            for rel in relations:
                rel.delete()
                logger.info(f"service<{rel.db_obj.service_id}-{rel.db_obj.service_instance_id}> deleted. ")

                # Put related services into collection
                service = mixed_service_mgr.get(rel.db_obj.service_id)
                services.append(service)

        # Clear all related shared services
        processed_service_ids = set()
        for service in services:
            if service.uuid in processed_service_ids:
                continue
            SharingReferencesManager(self.module).clear_related(service)
            processed_service_ids.add(service.uuid)

    def delete_engine_apps(self):
        """删除与当前模块关联的 EngineApp"""
        delete_module_related_res(self.module)

    def delete_module(self):
        """删除模块的数据库记录(真删除)"""
        self.module.delete()


PresetServiceSpecs = Dict[str, Dict]


class DefaultServicesBinder:
    """A helper type for binding module's default services"""

    def __init__(self, module: Module):
        self.module = module
        self.application = self.module.application

    def bind(self):
        """Bind default services which were configured in 2 sources:

        - Module's source template config
        - Application's specs(for default modules only)
        """
        services = self.find_services_from_template()
        self._bind(services)

    def find_services_from_template(self) -> PresetServiceSpecs:
        """find default services defined in module template"""
        try:
            tmpl_mgr = TemplateRuntimeManager(self.module.source_init_template)
            return tmpl_mgr.get_preset_services_config()
        except Template.DoesNotExist:
            return {}

    def _bind(self, services: PresetServiceSpecs):
        """Bind current module with given services"""
        # The value of `services` contains specs, the specs used to be a parameter for
        # `bind_service` but now it's not used anymore, so we just ignore it.
        for service_name in services:
            try:
                service_obj = mixed_service_mgr.find_by_name(service_name)
            except ServiceObjNotFound:
                logger.exception("应用<%s>获取预设增强服务<%s>失败", self.application.code, service_name)
                continue

            mixed_service_mgr.bind_service_use_first_plan(service_obj, self.module)


def make_engine_app_name(module: Module, app_code: str, env: str) -> str:
    # 兼容考虑，如果模块名为 default 则不在 engine 名字中插入 module 名
    if module.name == ModuleName.DEFAULT.value:
        name = f"{DEFAULT_ENGINE_APP_PREFIX}-{app_code}-{env}"
    else:
        # use `-m-` to divide module name and app code
        name = f"{DEFAULT_ENGINE_APP_PREFIX}-{app_code}-m-{module.name}-{env}"
    return name
