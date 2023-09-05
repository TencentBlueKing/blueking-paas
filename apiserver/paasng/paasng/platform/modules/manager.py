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
"""Management functions for application module, may include:

- Module initialization
- Module deletetion / recycle
"""
import logging
from collections import namedtuple
from contextlib import contextmanager
from operator import attrgetter
from typing import Any, Dict, List, Optional

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils.translation import gettext as _

from paas_wl.cluster.shim import EnvClusterService
from paas_wl.cnative.specs.crd.bk_app import BkAppResource
from paas_wl.cnative.specs.models import AppModelResource, create_app_resource, generate_bkapp_name
from paas_wl.platform.api import create_app_ignore_duplicated, delete_module_related_res, update_metadata_by_env
from paas_wl.platform.applications.constants import WlAppType
from paasng.dev_resources.servicehub.exceptions import ServiceObjNotFound
from paasng.dev_resources.servicehub.manager import mixed_service_mgr
from paasng.dev_resources.servicehub.sharing import SharingReferencesManager
from paasng.dev_resources.sourcectl.connector import get_repo_connector
from paasng.dev_resources.sourcectl.docker.models import init_image_repo
from paasng.dev_resources.templates.constants import TemplateType
from paasng.dev_resources.templates.manager import AppBuildPack, TemplateRuntimeManager
from paasng.dev_resources.templates.models import Template
from paasng.engine.constants import RuntimeType
from paasng.engine.models import EngineApp
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.applications.specs import AppSpecs
from paasng.platform.log.shim import setup_env_log_model
from paasng.platform.modules.constants import DEFAULT_ENGINE_APP_PREFIX, ModuleName
from paasng.platform.modules.exceptions import ModuleInitializationError
from paasng.platform.modules.helpers import ModuleRuntimeBinder, get_image_labels_by_module
from paasng.platform.modules.models import AppSlugBuilder, AppSlugRunner, BuildConfig, Module
from paasng.platform.modules.specs import ModuleSpecs
from paasng.platform.oauth2.utils import get_oauth2_client_secret
from paasng.utils.addons import ReplaceableFunction
from paasng.utils.basic import get_username_by_bkpaas_user_id
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
                region=self.module.region, tmpl_name=self.module.source_init_template
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

    default_environments = ['stag', 'prod']

    def __init__(self, module: Module):
        self.module = module
        self.application = self.module.application

    def make_engine_app_name(self, env: str) -> str:
        return make_engine_app_name(self.module, self.application.code, env)

    def make_engine_meta_info(self, env: ModuleEnvironment) -> Dict[str, Any]:
        ext_metadata = make_app_metadata(env)
        return {
            'paas_app_code': self.application.code,
            'module_name': self.module.name,
            'environment': env.environment,
            **ext_metadata,
        }

    @transaction.atomic
    def create_engine_apps(self, environments: Optional[List[str]] = None, cluster_name: Optional[str] = None):
        """Create engine app instances for application"""
        environments = environments or self.default_environments
        wl_app_type = (
            WlAppType.CLOUD_NATIVE if self.application.type == ApplicationType.CLOUD_NATIVE else WlAppType.DEFAULT
        )

        for environment in environments:
            name = self.make_engine_app_name(environment)
            engine_app = self._get_or_create_engine_app(name, wl_app_type)
            env = ModuleEnvironment.objects.create(
                application=self.application, module=self.module, engine_app_id=engine_app.id, environment=environment
            )
            # bind env to cluster
            EnvClusterService(env).bind_cluster(cluster_name)

            # Update metadata
            engine_app_meta_info = self.make_engine_meta_info(env)
            update_metadata_by_env(env, engine_app_meta_info)
        return

    def initialize_vcs_with_template(
        self,
        repo_type: Optional[str] = None,
        repo_url: Optional[str] = None,
        repo_auth_info: Optional[dict] = None,
        source_dir: str = '',
    ):
        """Initialize module vcs with source template

        :param repo_type: the type of repository provider, used when source_origin is `AUTHORIZED_VCS`
        :param repo_url: the address of repository, used when source_origin is `AUTHORIZED_VCS`
        :param repo_auth_info: the auth of repository
        :param source_dir: The work dir, which containing Procfile.
        """
        if not self._should_initialize_vcs():
            logger.info(
                'Skip initializing template for application:<%s>/<%s>', self.application.code, self.module.name
            )
            return {'code': 'OK', "extra_info": {}, "dest_type": 'null'}

        client_secret = get_oauth2_client_secret(self.application.code, self.application.region)
        context = {
            'region': self.application.region,
            'owner_username': get_username_by_bkpaas_user_id(self.application.owner),
            'app_code': self.application.code,
            'app_secret': client_secret,
            'app_name': self.application.name,
        }

        if not repo_type:
            raise ValueError('repo type must not be None')

        connector = get_repo_connector(repo_type, self.module)
        connector.bind(repo_url, source_dir=source_dir, repo_auth_info=repo_auth_info)

        # Only run syncing procedure when `source_init_template` is valid
        if not Template.objects.filter(name=self.module.source_init_template, type=TemplateType.NORMAL).exists():
            return {'code': 'OK', "extra_info": {}, "dest_type": 'null'}

        result = connector.sync_templated_sources(context)

        if result.is_success():
            return {'code': 'OK', "extra_info": result.extra_info, "dest_type": result.dest_type}
        return {'code': result.error}

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
        if module_specs.runtime_type == RuntimeType.CUSTOM_IMAGE:
            return False

        return True

    def bind_default_services(self):
        """Bind default services after module creation"""
        DefaultServicesBinder(self.module).bind()

    def initialize_docker_build_config(self):
        """初始化 Dockerfile 类型的构建配置"""
        tmpl_mgr = TemplateRuntimeManager(region=self.module.region, tmpl_name=self.module.source_init_template)
        cfg = tmpl_mgr.get_docker_build_config()
        db_instance = BuildConfig.objects.get_or_create_by_module(self.module)
        db_instance.update_with_build_method(
            build_method=cfg.build_method,
            dockerfile_path=cfg.dockerfile_path,
            docker_build_args=cfg.docker_build_args,
        )

    def bind_default_runtime(self):
        """Bind slugbuilder/slugrunner/buildpacks after module creation"""
        runtime_labels = get_image_labels_by_module(self.module)
        self.bind_runtime_by_labels(runtime_labels)

    def bind_runtime_by_labels(self, labels: Dict[str, str], contain_hidden: bool = False):
        """Bind slugbuilder/slugrunner/buildpacks by labels"""
        try:
            slugbuilder = AppSlugBuilder.objects.select_default_runtime(self.module.region, labels, contain_hidden)
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

    def initialize_log_config(self):
        for env in self.module.get_envs():
            setup_env_log_model(env)

    def initialize_app_model_resource(self, manifest: Optional[Dict] = None):
        # 只有云原生应用需要在创建模块后初始化 AppModelResource
        if self.application.type != ApplicationType.CLOUD_NATIVE:
            return

        res_name = generate_bkapp_name(self.module)
        # 即使没有指定 manifest，也会默认初始化 AppModelResource，
        # 但这仅仅是占位数据，应当在第一次部署时候被源码库中的配置替换
        resource = create_app_resource(name=res_name, image='stub')
        if manifest:
            manifest['metadata']['name'] = res_name
            resource = BkAppResource(**manifest)

        app = self.application
        AppModelResource.objects.create_from_resource(
            region=app.region,
            application_id=app.id,
            module_id=self.module.id,
            resource=resource,
        )

    def _get_or_create_engine_app(self, name: str, app_type: WlAppType) -> EngineApp:
        """Create or get existed engine app by given name"""
        info = create_app_ignore_duplicated(self.application.region, name, app_type)
        engine_app = EngineApp.objects.create(
            id=info.uuid, name=info.name, owner=self.application.owner, region=self.application.region
        )
        return engine_app


ModuleInitResult = namedtuple('ModuleInitResult', 'source_init_result')


@contextmanager
def _humanize_exception(step_name: str, message: str):
    """Transform all exception when initialize module into ModuleInitializationError with human friendly message"""
    try:
        yield
    except Exception as e:
        logger.exception("An exception occurred during `%s`, detail: %s", step_name, e)
        raise ModuleInitializationError(message) from e


def init_module_in_view(*args, **kwargs) -> ModuleInitResult:
    """Initialize a module in view function, see `initialize_module(...)` for more information

    :raises: APIError when any error occurs
    """
    try:
        return initialize_module(*args, **kwargs)
    except ModuleInitializationError as e:
        raise error_codes.CANNOT_CREATE_APP.f(str(e))


def initialize_smart_module(module: Module, cluster_name: Optional[str] = None):
    """Initialize a module for s-mart app"""
    module_initializer = ModuleInitializer(module)
    module_spec = ModuleSpecs(module)

    # Create engine apps first
    with _humanize_exception('create_engine_apps', _('服务暂时不可用，请稍候再试')):
        module_initializer.create_engine_apps(cluster_name=cluster_name)

    with _humanize_exception('bind_default_services', _('绑定初始增强服务失败，请稍候再试')):
        module_initializer.bind_default_services()

    if module_spec.runtime_type == RuntimeType.BUILDPACK:
        # bind heroku runtime, such as slug builder/runner and buildpacks
        with _humanize_exception(_('绑定初始运行环境失败，请稍候再试'), 'bind default runtime'):
            module_initializer.bind_default_runtime()

    with _humanize_exception("initialize_log_config", _("日志模块初始化失败, 请稍候再试")):
        module_initializer.initialize_log_config()

    return ModuleInitResult(source_init_result={})


def initialize_module(
    module: Module,
    repo_type: str,
    repo_url: Optional[str],
    repo_auth_info: Optional[dict],
    source_dir: str = '',
    cluster_name: Optional[str] = None,
    manifest: Optional[Dict] = None,
) -> ModuleInitResult:
    """Initialize a module

    :param repo_type: sourcectl type name, see SourceTypeSpecConfig table data for all names
    :param repo_url: The address of repository, such as "git://x.git.com/repo"
    :param repo_auth_info: The auth of repository, such as {"username": "ddd", "password": "www"}
    :param source_dir: The work dir, which containing Procfile.
    :param cluster_name: optional engine cluster name
    :param manifest: optional cnative module manifest(only build_method=custom_image required)
    :raises: ModuleInitializationError when any steps failed
    """
    module_initializer = ModuleInitializer(module)
    module_spec = ModuleSpecs(module)

    # Create engine apps first
    with _humanize_exception('create_engine_apps', _('服务暂时不可用，请稍候再试')):
        module_initializer.create_engine_apps(cluster_name=cluster_name)

    source_init_result = {}
    if module_spec.has_vcs:
        # initialize module vcs with template if required
        with _humanize_exception('initialize_app_source', _('代码初始化过程失败，请稍候再试')):
            source_init_result = module_initializer.initialize_vcs_with_template(
                repo_type, repo_url, repo_auth_info=repo_auth_info, source_dir=source_dir
            )

    if module_spec.templated_source_enabled:
        with _humanize_exception('bind_default_runtime', _('绑定初始运行环境失败，请稍候再试')):
            tmpl_mgr = TemplateRuntimeManager(region=module.region, tmpl_name=module.source_init_template)
            if tmpl_mgr.template.runtime_type == RuntimeType.BUILDPACK:
                # bind heroku runtime, such as slug builder/runner and buildpacks
                module_initializer.bind_default_runtime()
            elif tmpl_mgr.template.runtime_type == RuntimeType.DOCKERFILE:
                # setup build_config, such as dockerfile path and build args
                module_initializer.initialize_docker_build_config()

    elif module_spec.runtime_type != RuntimeType.CUSTOM_IMAGE:
        # Matches source_origin type: Lesscode or BK_PLUGIN
        with _humanize_exception('bind_default_runtime', _('绑定初始运行环境失败，请稍候再试')):
            # bind heroku runtime, such as slug builder/runner and buildpacks
            module_initializer.bind_default_runtime()
    elif not manifest:
        # Matches source_origin type: IMAGE_REGISTRY and NOT cloud native app
        with _humanize_exception('config_image_registry', _('配置镜像 Registry 失败，请稍候再试')):
            init_image_repo(module, repo_url or '', source_dir, repo_auth_info or {})

    with _humanize_exception('bind_default_services', _('绑定初始增强服务失败，请稍候再试')):
        module_initializer.bind_default_services()

    with _humanize_exception("initialize_log_config", _("日志模块初始化失败, 请稍候再试")):
        module_initializer.initialize_log_config()

    with _humanize_exception("initialize_app_model_resource", _("初始化应用模型失败, 请稍候再试")):
        module_initializer.initialize_app_model_resource(manifest)

    return ModuleInitResult(source_init_result=source_init_result)


class ModuleCleaner:
    def __init__(self, module: Module):
        self.module = module

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
                service = mixed_service_mgr.get(rel.db_obj.service_id, self.module.region)
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
        services = self.find_services_from_app_specs()
        services.update(self.find_services_from_template())
        self._bind(services)

    def find_services_from_app_specs(self) -> PresetServiceSpecs:
        """find default services for current application"""
        # Only affects default module
        if not self.module.is_default:
            return {}
        return AppSpecs(self.application).preset_services

    def find_services_from_template(self) -> PresetServiceSpecs:
        """find default services defined in module template"""
        try:
            tmpl_mgr = TemplateRuntimeManager(region=self.module.region, tmpl_name=self.module.source_init_template)
            return tmpl_mgr.get_preset_services_config()
        except Template.DoesNotExist:
            return {}

    def _bind(self, services: PresetServiceSpecs):
        """Bind current module with given services"""
        for service_name, config in services.items():
            try:
                service_obj = mixed_service_mgr.find_by_name(service_name, self.application.region)
            except ServiceObjNotFound:
                logger.exception("应用<%s>获取预设增强服务<%s>失败", self.application.code, service_name)
                continue

            mixed_service_mgr.bind_service(service_obj, self.module, config.get("specs"))


def make_engine_app_name(module: Module, app_code: str, env: str) -> str:
    # 兼容考虑，如果模块名为 default 则不在 engine 名字中插入 module 名
    if module.name == ModuleName.DEFAULT.value:
        name = f'{DEFAULT_ENGINE_APP_PREFIX}-{app_code}-{env}'
    else:
        # use `-m-` to divide module name and app code
        name = f'{DEFAULT_ENGINE_APP_PREFIX}-{app_code}-m-{module.name}-{env}'
    return name
