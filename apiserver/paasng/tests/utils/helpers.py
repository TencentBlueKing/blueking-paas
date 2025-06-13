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

import copy
import datetime
import uuid
from contextlib import ExitStack, contextmanager
from typing import Any, Callable, ContextManager, Dict, List, Optional
from unittest import mock

from django.conf import settings
from django.test.utils import override_settings
from django_dynamic_fixture import G

from paas_wl.bk_app.applications.api import CreatedAppInfo, create_app_ignore_duplicated, update_metadata_by_env
from paas_wl.bk_app.applications.constants import WlAppType
from paas_wl.bk_app.cnative.specs.constants import ApiVersion
from paas_wl.core.resource import generate_bkapp_name
from paas_wl.infras.cluster.entities import AllocationContext
from paas_wl.infras.cluster.shim import ClusterAllocator, EnvClusterService
from paasng.accessories.log.shim import setup_env_log_model
from paasng.accessories.log.shim.setup_elk import ClusterElasticSearchConfig
from paasng.accessories.publish.market.constant import ProductSourceUrlType
from paasng.accessories.publish.market.models import MarketConfig
from paasng.core.core.storages.sqlalchemy import filter_field_values, has_column, legacy_db
from paasng.core.region.states import load_regions_from_settings
from paasng.core.tenant.constants import AppTenantMode
from paasng.core.tenant.user import DEFAULT_TENANT_ID
from paasng.infras.oauth2.utils import create_oauth2_client
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import Application, ModuleEnvironment
from paasng.platform.applications.signals import post_create_application
from paasng.platform.applications.utils import create_default_module
from paasng.platform.engine.constants import AppEnvName
from paasng.platform.engine.models import EngineApp
from paasng.platform.modules.constants import ExposedURLType, SourceOrigin
from paasng.platform.modules.handlers import setup_module_log_model
from paasng.platform.modules.manager import ModuleInitializer, make_engine_app_name
from paasng.platform.modules.models import BuildConfig, Module
from paasng.platform.modules.specs import ModuleSpecs
from paasng.platform.sourcectl.source_types import get_sourcectl_types
from paasng.utils.configs import RegionAwareConfig

from . import auth
from .basic import generate_random_string

try:
    from paasng.infras.legacydb_te.models import LApplication, LApplicationTag
except ImportError:
    from paasng.infras.legacydb.models import LApplication, LApplicationTag


def initialize_application(application, *args, **kwargs):
    """Initialize an application"""
    module = create_default_module(application)
    create_oauth2_client(application.code, application.app_tenant_mode, application.app_tenant_id)

    initialize_module(module, *args, **kwargs)

    # Disable market config by default
    MarketConfig.objects.create(
        application=application,
        enabled=False,
        source_module=module,
        source_url_type=ProductSourceUrlType.ENGINE_PROD_ENV.value,
        source_tp_url=None,
    )


def initialize_module(module, repo_type=None, repo_url="", additional_modules=None):
    """Mocked function for initializing new module."""
    if additional_modules is None:
        additional_modules = []

    # Use a random sourcectl_type as default
    repo_type = repo_type or get_sourcectl_types().names.get_default()

    default_mockers: List[ContextManager] = [
        mock.patch("paasng.platform.modules.manager.make_app_metadata"),
        mock.patch("paasng.platform.sourcectl.svn.client.SvnRepositoryClient"),
        contextmanager(_mock_wl_services_in_creation)(),
        mock.patch(
            "paasng.platform.modules.handlers.apply_async_on_commit",
            side_effect=lambda callback, args: callback(*args),
        ),
    ]
    # 通过 Mock 被跳过的应用流程（性能原因）
    optional_mockers = {
        # 初始化模块代码，同步到 SVN 等后端
        "sourcectl": mock.patch("paasng.platform.modules.manager.ModuleInitializer.initialize_vcs_with_template"),
    }
    for mod in additional_modules:
        optional_mockers.pop(mod, None)

    with ExitStack() as stack:
        [stack.enter_context(mocker) for mocker in default_mockers]
        [stack.enter_context(mocker) for mocker in optional_mockers.values()]

        module_initializer = ModuleInitializer(module)
        module_initializer.create_engine_apps()

        module_spec = ModuleSpecs(module)
        if module_spec.source_origin in [
            SourceOrigin.IMAGE_REGISTRY,
            SourceOrigin.CNATIVE_IMAGE,
            SourceOrigin.S_MART,
        ] or module_spec.app_specs.type_specs in [
            ApplicationType.ENGINELESS_APP,
        ]:
            module.source_init_template = ""

        # Set-up the repository data
        if repo_url:
            module.source_origin = SourceOrigin.AUTHORIZED_VCS
            module.source_init_template = settings.DUMMY_TEMPLATE_NAME

        module.save()
        module_initializer.initialize_vcs_with_template(repo_type, repo_url)
        setup_module_log_model(module_id=module.pk)


def create_app(
    owner_username: Optional[str] = None,
    additional_modules: Optional[List] = None,
    repo_type: str = "",
    region: Optional[str] = None,
    force_info: Optional[dict] = None,
):
    """Create a simple application, for testing purpose only

    :param additional_modules: enable additional applications modules, choose from ['deploy_phases', 'sourcectl']
    :param owner_username: username of owner
    """
    if additional_modules is None:
        additional_modules = []

    if owner_username:
        user = auth.create_user(username=owner_username)
    else:
        user = auth.create_user()

    region = region or settings.DEFAULT_REGION_NAME

    force_info = force_info or {}
    app_code = force_info.get("app_code") or "ut" + generate_random_string(length=6)
    name = app_code.replace("-", "")
    fields = dict(name=name, name_en=name, language="Python", region=region)

    # 默认为全租户应用
    application = G(
        Application,
        owner=user.pk,
        creator=user.pk,
        code=app_code,
        logo=None,
        app_tenant_mode=AppTenantMode.GLOBAL,
        app_tenant_id="",
        tenant_id=DEFAULT_TENANT_ID,
        **fields,
    )

    # First try Svn, then GitLab, then Default
    if not repo_type:
        try:
            try:
                sourcectl_name = get_sourcectl_types().names.bk_svn
            except KeyError:
                sourcectl_name = get_sourcectl_types().names.git_lab
        except KeyError:
            sourcectl_name = get_sourcectl_types().names.get_default()
    else:
        sourcectl_name = get_sourcectl_types().names.get(repo_type)

    basic_type = get_sourcectl_types().get(sourcectl_name).basic_type
    default_repo_url = f"{basic_type}://127.0.0.1:8080/app"

    initialize_application(
        application, repo_type=sourcectl_name, repo_url=default_repo_url, additional_modules=additional_modules
    )
    module = application.get_default_module()
    # bind build_config
    BuildConfig.objects.get_or_create_by_module(module)

    # Send post-creation signal
    post_create_application.send(sender=create_app, application=application)

    # Update the region field after initialize to avoid exceptions
    application.region = region
    application.save()
    module.region = region
    module.save()
    return application


def create_legacy_application(code: Optional[str] = None):
    """Create a simple legacy application, for testing purpose only

    :param code: The application code, default to a random string.
    """
    session = legacy_db.get_scoped_session()
    app_code = code if code else generate_random_string(length=12)
    values = dict(
        code=app_code,
        name=app_code,
        from_paasv3=0,
        migrated_to_paasv3=0,
        logo="",
        introduction="",
        creater="",
        created_date=datetime.datetime.now(),
        created_state=0,
        app_type=1,
        state=1,  # 开发中
        width=890,
        height=550,
        deploy_env=102,
        init_svn_version=0,
        is_already_online=1,
        is_already_test=1,
        is_code_private=1,
        first_test_time=datetime.datetime.now(),
        first_online_time=datetime.datetime.now(),
        dev_time=0,
        app_cate=0,
        is_offical=0,
        is_base=0,
        audit_state=0,
        isneed_reaudit=1,
        svn_domain="",  # SVN域名, 真正注册的时候完善
        use_celery=0,  # app是否使用celery，确定一下是否需要
        use_celery_beat=0,  # app是否使用celery beat，确定一下是否需要
        usecount_ied=0,
        is_select_svn_dir=1,
        is_lapp=0,  # 是否是轻应用
        use_mobile_test=0,
        use_mobile_online=0,
        is_display=1,
        is_mapp=0,
        is_default=0,
        is_open=0,
        is_max=0,
        display_type="app",
        issetbar=1,
        isflash=0,
        isresize=1,
        usecount=0,
        starnum=0,  # 星级评分
        starnum_ied=0,  # 星级评分
        deploy_ver=settings.DEFAULT_REGION_NAME,
        cpu_limit=1024,  # 上线或提测CPU限制
        mem_limit=512,  # 上线或提测内存限制
        open_mode="desktop",
    )
    values = adaptive_lapplication_fields(values)
    app = LApplication(**values)
    session.add(app)
    session.commit()
    return app


def adaptive_lapplication_fields(field_values: Dict[str, Any]) -> Dict[str, Any]:
    """Update a pair of LApplication field values, make it suitable for current environment
    by removing and adding some fields.
    """
    # Remove fields which were absent in open-source version
    field_values = filter_field_values(LApplication, field_values)
    # Add fields which were required for open-source version only
    if has_column(LApplication, "is_saas"):
        field_values.update(
            is_saas=True,
            is_sysapp=True,
            is_third=False,
            is_platform=False,
            migrated_to_paasv3=False,
            is_resize=True,
            is_setbar=True,
            is_use_celery=False,
            is_use_celery_beat=False,
            use_count=0,
        )
    return field_values


def adaptive_lapplicationtag_fields(field_values: Dict[str, Any]) -> Dict[str, Any]:
    """Update a pair of LApplicationTag field values, make it suitable for current environment
    by removing and adding some fields.
    """
    # Remove fields which were absent in open-source version
    return filter_field_values(LApplicationTag, field_values)


@contextmanager
def override_region_configs(region: str, update_conf_func: Callable):
    """Override region configs during testing"""
    new_region_configs: Dict[str, List] = {"regions": []}
    for _orig_config in settings.REGION_CONFIGS["regions"]:
        region_config = copy.deepcopy(_orig_config)

        # Call hook function to modify the original region config
        if region_config["name"] == region:
            update_conf_func(region_config)
        new_region_configs["regions"].append(region_config)

    with override_settings(REGION_CONFIGS=new_region_configs):
        load_regions_from_settings()
        yield

    # Restore original settings
    load_regions_from_settings()


@contextmanager
def configure_regions(regions: List[str]):
    """Configure multi regions with default template.

    :param regions: A list of region names, the first item will be set as the default region.
    """
    new_region_configs: Dict[str, List] = {"regions": []}
    for region in regions:
        config = copy.deepcopy(settings.DEFAULT_REGION_TEMPLATE)
        config["name"] = region
        new_region_configs["regions"].append(config)

    region_aware_names = ["ACCESS_CONTROL_CONFIG"]
    region_aware_changes = {}
    for name in region_aware_names:
        value = getattr(settings, name)
        config = RegionAwareConfig(value)
        if not config.lookup_with_region:
            continue

        # Set value for new region
        _tmpl_value = next(iter(config.data.values()))
        for region in regions:
            value["data"][region] = _tmpl_value
        region_aware_changes[name] = value

    with override_settings(REGION_CONFIGS=new_region_configs, DEFAULT_REGION_NAME=regions[0], **region_aware_changes):
        load_regions_from_settings()
        yield

    # Restore original settings
    load_regions_from_settings()


# Stores pending actions related with workloads during app creation
_faked_wl_apps = {}
_faked_env_metadata = {}


def _mock_wl_services_in_creation():
    """Mock workloads related functions related with app creation, the calls being
    mocked will be stored and can be used for restoring data later.
    """

    def fake_create_app_ignore_duplicated(region: str, name: str, type_: str, tenant_id: str):
        obj = CreatedAppInfo(uuid=uuid.uuid4(), name=name, type=WlAppType(type_))

        # Store params in global, so we can manually create the objects later.
        _faked_wl_apps[obj.uuid] = (region, name, type_, tenant_id)
        return obj

    def fake_update_metadata_by_env(env, metadata_part):
        # Store params in global, so we can manually update the metadata later.
        if env.id not in _faked_env_metadata:
            _faked_env_metadata[env.id] = metadata_part
        else:
            _faked_env_metadata[env.id].update(metadata_part)

    mock_cluster_setup_elk = mock.Mock()
    mock_cluster_setup_elk.uuid = uuid.uuid4()
    mock_cluster_es_config_queryset = mock.Mock()
    mock_cluster_es_config_queryset.first.return_value = None
    with (
        mock.patch(
            "paasng.platform.modules.manager.create_app_ignore_duplicated", new=fake_create_app_ignore_duplicated
        ),
        mock.patch("paasng.platform.modules.manager.update_metadata_by_env", new=fake_update_metadata_by_env),
        mock.patch("paasng.platform.modules.manager.EnvClusterService"),
        mock.patch("paasng.platform.modules.manager.get_exposed_url_type", return_value=ExposedURLType.SUBPATH),
        mock.patch("paasng.accessories.log.shim.EnvClusterService") as fake_log,
        mock.patch("paasng.accessories.log.shim.setup_elk.EnvClusterService") as fake_setup_elk,
        mock.patch.object(ClusterElasticSearchConfig.objects, "filter") as mock_filter,
    ):
        fake_log().get_cluster().has_feature_flag.return_value = False
        fake_setup_elk.return_value.get_cluster.return_value = mock_cluster_setup_elk
        mock_filter.return_value = mock_cluster_es_config_queryset
        yield


def create_pending_wl_apps(bk_app: Application, cluster_name: str):
    """Create WlApp objects of the given application in workloads, these objects

    should have been created during application creation, but weren't because the
    `create_app_ignore_duplicated` function was mocked out.
    """
    from paas_wl.bk_app.applications.api import update_metadata_by_env
    from paas_wl.bk_app.applications.models import WlApp

    for module in bk_app.modules.all():
        for env in module.envs.all():
            # Create WlApps and update metadata
            if args := _faked_wl_apps.get(env.engine_app_id):
                region, name, type_, tenant_id = args
                if WlApp.objects.filter(name=name).exists():
                    continue
                wl_app = WlApp.objects.create(
                    uuid=env.engine_app_id, region=region, name=name, type=type_, tenant_id=tenant_id
                )
                latest_config = wl_app.latest_config
                latest_config.cluster = cluster_name
                latest_config.save()
            if metadata := _faked_env_metadata.get(env.id):
                update_metadata_by_env(env, metadata)


def create_cnative_app(
    owner_username: Optional[str] = None,
    repo_type: str = "",
    region: Optional[str] = None,
    force_info: Optional[dict] = None,
    cluster_name: Optional[str] = None,
):
    """Create a cloud-native application, for testing purpose only"""
    if owner_username:
        user = auth.create_user(username=owner_username)
    else:
        user = auth.create_user()
    region = region or settings.DEFAULT_REGION_NAME

    # Create the Application object
    force_info = force_info or {}
    app_code = force_info.get("app_code") or "ut" + generate_random_string(length=6)
    name = app_code.replace("-", "")
    application = G(
        Application,
        type=ApplicationType.CLOUD_NATIVE,
        region=region,
        owner=user.pk,
        creator=user.pk,
        code=app_code,
        logo=None,
        name=name,
        name_en=name,
        # 默认为全租户应用
        app_tenant_mode=AppTenantMode.GLOBAL,
        app_tenant_id="",
        tenant_id=DEFAULT_TENANT_ID,
    )
    create_oauth2_client(application.code, application.app_tenant_mode, application.app_tenant_id)

    # First try Svn, then GitLab, then Default
    if not repo_type:
        try:
            try:
                sourcectl_name = get_sourcectl_types().names.bk_svn
            except KeyError:
                sourcectl_name = get_sourcectl_types().names.git_lab
        except KeyError:
            sourcectl_name = get_sourcectl_types().names.get_default()
    else:
        sourcectl_name = get_sourcectl_types().names.get(repo_type)

    basic_type = get_sourcectl_types().get(sourcectl_name).basic_type
    default_repo_url = f"{basic_type}://127.0.0.1:8080/app"

    create_default_module(application)
    # TODO: 使用新的创建模块逻辑
    with contextmanager(_mock_wl_services_in_creation)():
        module = application.get_default_module()
        initialize_simple_cnative(module, "", cluster_name=cluster_name)
        module_initializer = ModuleInitializer(module)
        # Set-up the repository data
        module.source_origin = SourceOrigin.AUTHORIZED_VCS
        module.source_init_template = settings.DUMMY_TEMPLATE_NAME
        module.save()
        module_initializer.initialize_vcs_with_template(sourcectl_name, default_repo_url)

    # Send post-creation signal
    post_create_application.send(sender=create_app, application=application)
    return application


def register_iam_after_create_application(application: Application):
    """
    默认为每个新建的蓝鲸应用创建三个用户组（管理者，开发者，运营者），以及该应用对应的分级管理员
    将 创建者 添加到 管理者用户组 以获取应用的管理权限，并添加为 分级管理员成员 以获取审批其他用户加入各个用户组的权限
    """
    from paasng.infras.iam.constants import NEVER_EXPIRE_DAYS
    from paasng.infras.iam.members.models import ApplicationGradeManager, ApplicationUserGroup
    from paasng.platform.applications.tenant import get_tenant_id_for_app
    from paasng.utils.basic import get_username_by_bkpaas_user_id
    from tests.utils.mocks.iam import StubBKIAMClient

    tenant_id = get_tenant_id_for_app(application.code)
    cli = StubBKIAMClient(tenant_id)
    creator = get_username_by_bkpaas_user_id(application.creator or application.owner)

    # 1. 创建分级管理员，并记录分级管理员 ID
    grade_manager_id = cli.create_grade_managers(application.code, application.name, creator)
    ApplicationGradeManager.objects.create(
        app_code=application.code, grade_manager_id=grade_manager_id, tenant_id=tenant_id
    )

    # 2. 将创建者，添加为分级管理员的成员
    cli.add_grade_manager_members(grade_manager_id, [creator])

    # 3. 创建默认的 管理者，开发者，运营者用户组
    user_groups = cli.create_builtin_user_groups(grade_manager_id, application.code)
    ApplicationUserGroup.objects.bulk_create(
        [
            ApplicationUserGroup(
                app_code=application.code, role=group["role"], user_group_id=group["id"], tenant_id=tenant_id
            )
            for group in user_groups
        ]
    )

    # 4. 为默认的三个用户组授权
    cli.grant_user_group_policies(application.code, application.name, user_groups)

    # 5. 将创建者添加到管理者用户组，返回数据中第一个即为管理者用户组信息
    cli.add_user_group_members(user_groups[0]["id"], [creator], NEVER_EXPIRE_DAYS)


def initialize_simple_cnative(
    module: Module,
    image: str,
    cluster_name: str | None = None,
    api_version: str = ApiVersion.V1ALPHA2,
    command: List[str] | None = None,
    args: List[str] | None = None,
    target_port: int | None = None,
) -> Dict:
    """Initialize a cloud-native application, return the initialized object

    :param module: Module object, a module can only be initialized once
    :param image: The container image of main process
    :param cluster_name: The name of cluster to deploy BkApp.
    :param command: Custom command
    :param args: Custom args
    :param target_port: Custom target port
    """
    model_res = create_cnative_app_model_resource(module, image, api_version, command, args, target_port)
    create_engine_apps(module.application, module, [AppEnvName.STAG, AppEnvName.PROD], cluster_name)
    return model_res


def create_cnative_app_model_resource(
    module: Module,
    image: str,
    api_version: str = ApiVersion.V1ALPHA2,
    command: List[str] | None = None,
    args: List[str] | None = None,
    target_port: int | None = None,
) -> Dict:
    """Create a cloud-native AppModelResource object"""
    from paas_wl.bk_app.cnative.specs.models import AppModelResource, create_app_resource

    application = module.application
    resource = create_app_resource(
        name=generate_bkapp_name(module),
        image=image,
        api_version=api_version,
        command=command,
        args=args,
        target_port=target_port,
    )
    model_resource = AppModelResource.objects.create_from_resource(application, str(module.id), resource)
    return {
        "application_id": model_resource.application_id,
        "module_id": model_resource.module_id,
        "manifest": model_resource.revision.json_value,
    }


def create_engine_apps(app: Application, module: Module, environments: List[str], cluster_name: str | None):
    """Create engine app instances for application"""
    for environment in environments:
        engine_app_name = make_engine_app_name(module, app.code, environment)
        # 先创建 EngineApp，再更新相关的配置（比如 cluster_name）
        info = create_app_ignore_duplicated(
            app.region,
            engine_app_name,
            WlAppType.CLOUD_NATIVE,
            app.tenant_id,
        )
        engine_app = EngineApp.objects.create(
            id=info.uuid,
            name=engine_app_name,
            owner=app.owner,
            region=app.region,
            tenant_id=app.tenant_id,
        )
        env = ModuleEnvironment.objects.create(
            application=app,
            module=module,
            engine_app_id=engine_app.id,
            environment=environment,
            tenant_id=app.tenant_id,
        )
        if not cluster_name:
            ctx = AllocationContext.from_module_env(env)
            cluster_name = ClusterAllocator(ctx).get_default().name

        EnvClusterService(env).bind_cluster(cluster_name)
        setup_env_log_model(env)

        # Update metadata
        engine_app_meta_info = ModuleInitializer(module).make_engine_meta_info(env)
        update_metadata_by_env(env, engine_app_meta_info)
