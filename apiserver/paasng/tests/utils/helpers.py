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
import copy
import datetime
import random
import uuid
from contextlib import ExitStack, contextmanager
from typing import Any, Callable, ContextManager, Dict, List, Optional
from unittest import mock

from django.conf import settings
from django.test import TestCase
from django.test.utils import override_settings
from django_dynamic_fixture import G

from paas_wl.platform.api import CreatedAppInfo
from paasng.cnative.services import initialize_simple
from paasng.dev_resources.sourcectl.source_types import get_sourcectl_types
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import Application
from paasng.platform.applications.signals import post_create_application
from paasng.platform.applications.utils import create_default_module
from paasng.platform.core.region import load_regions_from_settings
from paasng.platform.core.storages.sqlalchemy import filter_field_values, has_column, legacy_db
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.manager import ModuleInitializer
from paasng.platform.oauth2.utils import create_oauth2_client
from paasng.publish.market.constant import ProductSourceUrlType
from paasng.publish.market.models import MarketConfig
from paasng.utils.configs import RegionAwareConfig
from tests.utils.mocks.engine import replace_cluster_service

from .auth import create_user

try:
    from paasng.platform.legacydb_te.models import LApplication, LApplicationTag
except ImportError:
    from paasng.platform.legacydb.models import LApplication, LApplicationTag


def initialize_application(application, *args, **kwargs):
    """Initialize an application"""
    module = create_default_module(application)
    create_oauth2_client(application.code, application.region)

    initialize_module(module, *args, **kwargs)

    # Disable market config by default
    MarketConfig.objects.create(
        region=application.region,
        application=application,
        enabled=False,
        source_module=module,
        source_url_type=ProductSourceUrlType.ENGINE_PROD_ENV.value,
        source_tp_url=None,
    )


def initialize_module(module, repo_type=None, repo_url='', additional_modules=None):
    """Mocked function for initializing new module."""
    if additional_modules is None:
        additional_modules = []

    # Use a random sourcectl_type as default
    repo_type = repo_type or get_sourcectl_types().names.get_default()

    default_mockers: List[ContextManager] = [
        mock.patch('paasng.platform.modules.manager.make_app_metadata'),
        mock.patch('paasng.dev_resources.sourcectl.connector.SvnRepositoryClient'),
        replace_cluster_service(),
        contextmanager(_mock_wl_services_in_creation)(),
    ]
    # 通过 Mock 被跳过的应用流程（性能原因）
    optional_mockers = {
        # 初始化模块代码，同步到 SVN 等后端
        'sourcectl': mock.patch('paasng.platform.modules.manager.ModuleInitializer.initialize_with_template'),
    }
    for mod in additional_modules:
        optional_mockers.pop(mod, None)

    with ExitStack() as stack:
        [stack.enter_context(mocker) for mocker in default_mockers]
        [stack.enter_context(mocker) for mocker in optional_mockers.values()]

        module_initializer = ModuleInitializer(module)
        module_initializer.create_engine_apps()

        # Set-up the repository data
        if repo_url:
            module.source_origin = SourceOrigin.AUTHORIZED_VCS
            module.source_init_template = settings.DUMMY_TEMPLATE_NAME
            module.save()
            module_initializer.initialize_with_template(repo_type, repo_url)


class BaseTestCaseWithApp(TestCase):
    """Base class with an application was pre-created"""

    application: Application
    app_region = settings.DEFAULT_REGION_NAME
    app_code = 'utest-app'
    app_extra_fields: Dict[str, Any] = {}

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = create_user()

        name = cls.app_code.replace('-', '')
        fields = dict(name=name, language='Python', region=cls.app_region)
        fields.update(cls.app_extra_fields)

        cls.application = G(Application, owner=cls.user.pk, code=cls.app_code, **fields)
        cls.default_repo_url = 'svn://svn.localhost:1773/app'
        initialize_application(cls.application, repo_url=cls.default_repo_url)
        cls.module = cls.application.get_default_module()

        # Update the region field after initialize to avoide exceptions
        cls.application.region = cls.app_region
        cls.application.save()
        cls.module.region = cls.app_region
        cls.module.save()


def create_app(
    owner_username: Optional[str] = None,
    additional_modules: Optional[List] = None,
    repo_type: str = '',
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
        user = create_user(username=owner_username)
    else:
        user = create_user()

    region = region or settings.DEFAULT_REGION_NAME

    force_info = force_info or {}
    app_code = force_info.get("app_code") or 'ut' + generate_random_string(length=6)
    name = app_code.replace('-', '')
    fields = dict(name=name, name_en=name, language='Python', region=region)

    application = G(Application, owner=user.pk, creator=user.pk, code=app_code, logo=None, **fields)

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
    default_repo_url = f'{basic_type}://127.0.0.1:8080/app'

    initialize_application(
        application, repo_type=sourcectl_name, repo_url=default_repo_url, additional_modules=additional_modules
    )
    module = application.get_default_module()

    # Send post-creation signal
    post_create_application.send(sender=create_app, application=application)

    # Update the region field after initialize to avoid exceptions
    application.region = region
    application.save()
    module.region = region
    module.save()
    return application


def create_legacy_application():
    """Create a simple legacy application, for testing purpose only"""
    session = legacy_db.get_scoped_session()
    app_code = generate_random_string(length=12)
    app_name = app_code
    values = dict(
        code=app_code,
        name=app_name,
        from_paasv3=0,
        migrated_to_paasv3=0,
        logo='',
        introduction='',
        creater='',
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
        display_type='app',
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
    if has_column(LApplication, 'is_saas'):
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
    new_region_configs: Dict[str, List] = {'regions': []}
    for _orig_config in settings.REGION_CONFIGS['regions']:
        region_config = copy.deepcopy(_orig_config)

        # Call hook function to modify the original region config
        if region_config['name'] == region:
            update_conf_func(region_config)
        new_region_configs['regions'].append(region_config)

    with override_settings(REGION_CONFIGS=new_region_configs):
        load_regions_from_settings()
        yield

    # Restore original settings
    load_regions_from_settings()


@contextmanager
def configure_regions(regions: List[str]):
    """Configure multi regions with default template"""
    new_region_configs: Dict[str, List] = {'regions': []}
    for region in regions:
        config = copy.deepcopy(settings.DEFAULT_REGION_TEMPLATE)
        config['name'] = region
        new_region_configs['regions'].append(config)

    region_aware_names = ['ACCESS_CONTROL_CONFIG']
    region_aware_changes = {}
    for name in region_aware_names:
        value = getattr(settings, name)
        config = RegionAwareConfig(value)
        if not config.lookup_with_region:
            continue

        # Set value for new region
        _tmpl_value = next(iter(config.data.values()))
        for region in regions:
            value['data'][region] = _tmpl_value
        region_aware_changes[name] = value

    with override_settings(REGION_CONFIGS=new_region_configs, DEFAULT_REGION=regions[0], **region_aware_changes):
        load_regions_from_settings()
        yield

    # Restore original settings
    load_regions_from_settings()


DFT_RANDOM_CHARACTER_SET = 'abcdefghijklmnopqrstuvwxyz' '0123456789'


def generate_random_string(length=30, chars=DFT_RANDOM_CHARACTER_SET):
    """Generates a non-guessable OAuth token

    OAuth (1 and 2) does not specify the format of tokens except that they
    should be strings of random characters. Tokens should not be guessable
    and entropy when generating the random characters is important. Which is
    why SystemRandom is used instead of the default random.choice method.
    """
    rand = random.SystemRandom()
    return ''.join(rand.choice(chars) for x in range(length))


# Stores pending actions related with workloads during app creation
_faked_wl_engine_apps = {}
_faked_env_metadata = {}


def _mock_wl_services_in_creation():
    """Mock workloads related functions related with app creation, the calls being
    mocked will be stored and can be used for restoring data later.
    """

    def fake_create_app_ignore_duplicated(region: str, name: str, type_: str):
        obj = CreatedAppInfo(uuid=uuid.uuid4(), name=name)

        # Store params in global, so we can manually create the objects later.
        _faked_wl_engine_apps[obj.uuid] = (region, name, type_)
        return obj

    def fake_update_metadata_by_env(env, metadata_part):
        # Store params in global, so we can manually update the metadata later.
        _faked_env_metadata[env.id] = metadata_part

    with mock.patch(
        'paasng.platform.modules.manager.create_app_ignore_duplicated', new=fake_create_app_ignore_duplicated
    ), mock.patch(
        'paasng.platform.modules.manager.update_metadata_by_env', new=fake_update_metadata_by_env
    ), mock.patch(
        "paasng.platform.modules.manager.get_region_cluster_helper"
    ), mock.patch(
        'paasng.cnative.services.create_app_ignore_duplicated', new=fake_create_app_ignore_duplicated
    ), mock.patch(
        "paasng.cnative.services.controller_client"
    ):
        yield


def create_pending_wl_engine_apps(bk_app: Application):
    """Create WlEngineApp objects of the given application in workloads, these objects
    should have been created during application creation, but weren't because the
    `create_app_ignore_duplicated` function was mocked out.

    :param bk_app: Application object.
    """
    from paas_wl.platform.api import update_metadata_by_env
    from paas_wl.platform.applications.models.app import WLEngineApp

    for module in bk_app.modules.all():
        for env in module.envs.all():
            # Create WLEngineApps and update metadata
            if args := _faked_wl_engine_apps.get(env.engine_app_id):
                region, name, type_ = args
                WLEngineApp.objects.create(uuid=env.engine_app_id, region=region, name=name, type=type_)
            if metadata := _faked_env_metadata.get(env.id):
                update_metadata_by_env(env, metadata)


def create_scene_tmpls():
    """创建单元测试用的场景 SaaS 模板"""
    from paasng.dev_resources.templates.constants import TemplateType
    from paasng.dev_resources.templates.models import Template

    repo_url = 'http://git.com/owner/scene_tmpl_proj'
    blob_url = f'file://{settings.BASE_DIR}/tests/extensions/scene_app/contents/scene-tmpl.tar.gz'

    Template.objects.get_or_create(
        name='scene_tmpl1',
        defaults={
            'type': TemplateType.SCENE,
            'display_name_zh_cn': '场景模板1',
            'display_name_en': 'scene_tmpl1',
            'description_zh_cn': '场景模板1描述',
            'description_en': 'scene_tmpl1_desc',
            'language': 'Python',
            'market_ready': True,
            'preset_services_config': {},
            'blob_url': {settings.DEFAULT_REGION_NAME: blob_url},
            'enabled_regions': [settings.DEFAULT_REGION_NAME],
            'required_buildpacks': [],
            'processes': {},
            'tags': ['Python'],
            'repo_url': repo_url,
        },
    )

    Template.objects.get_or_create(
        name='scene_tmpl2',
        defaults={
            'type': TemplateType.SCENE,
            'display_name_zh_cn': '场景模板2',
            'display_name_en': 'scene_tmpl2',
            'description_zh_cn': '场景模板2描述',
            'description_en': 'scene_tmpl2_desc',
            'language': 'Go',
            'market_ready': True,
            'preset_services_config': {},
            'blob_url': {settings.DEFAULT_REGION_NAME: blob_url},
            'enabled_regions': [settings.DEFAULT_REGION_NAME],
            'required_buildpacks': [],
            'processes': {},
            'tags': ['Go'],
            'repo_url': repo_url,
        },
    )

    Template.objects.get_or_create(
        name='scene_tmpl3',
        defaults={
            'type': TemplateType.SCENE,
            'display_name_zh_cn': '场景模板3',
            'display_name_en': 'scene_tmpl3',
            'description_zh_cn': '场景模板3描述',
            'description_en': 'scene_tmpl3_desc',
            'language': 'PHP',
            'market_ready': True,
            'preset_services_config': {},
            'blob_url': {settings.DEFAULT_REGION_NAME: blob_url},
            'enabled_regions': [settings.DEFAULT_REGION_NAME],
            'required_buildpacks': [],
            'processes': {},
            'tags': ['PHP', 'legacy'],
            'repo_url': repo_url,
        },
    )


def create_cnative_app(
    owner_username: Optional[str] = None,
    region: Optional[str] = None,
    force_info: Optional[dict] = None,
    cluster_name: Optional[str] = None,
):
    """Create a cloud-native application, for testing purpose only

    :param owner_username: username of owner
    """
    if owner_username:
        user = create_user(username=owner_username)
    else:
        user = create_user()
    region = region or settings.DEFAULT_REGION_NAME

    # Create the Application object
    force_info = force_info or {}
    app_code = force_info.get("app_code") or 'ut' + generate_random_string(length=6)
    name = app_code.replace('-', '')
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
    )

    create_default_module(application)
    with replace_cluster_service(), contextmanager(_mock_wl_services_in_creation)():
        initialize_simple(application.get_default_module(), {}, cluster_name=cluster_name)
    # Send post-creation signal
    post_create_application.send(sender=create_app, application=application)
    return application


def register_iam_after_create_application(application: Application):
    """
    默认为每个新建的蓝鲸应用创建三个用户组（管理者，开发者，运营者），以及该应用对应的分级管理员
    将 创建者 添加到 管理者用户组 以获取应用的管理权限，并添加为 分级管理员成员 以获取审批其他用户加入各个用户组的权限
    """
    from paasng.accessories.iam.constants import NEVER_EXPIRE_DAYS
    from paasng.accessories.iam.members.models import ApplicationGradeManager, ApplicationUserGroup
    from paasng.utils.basic import get_username_by_bkpaas_user_id
    from tests.utils.mocks.iam import StubBKIAMClient

    cli = StubBKIAMClient()
    creator = get_username_by_bkpaas_user_id(application.creator or application.owner)

    # 1. 创建分级管理员，并记录分级管理员 ID
    grade_manager_id = cli.create_grade_managers(application.code, application.name, creator)
    ApplicationGradeManager.objects.create(app_code=application.code, grade_manager_id=grade_manager_id)

    # 2. 将创建者，添加为分级管理员的成员
    cli.add_grade_manager_members(grade_manager_id, [creator])

    # 3. 创建默认的 管理者，开发者，运营者用户组
    user_groups = cli.create_builtin_user_groups(grade_manager_id, application.code)
    ApplicationUserGroup.objects.bulk_create(
        [
            ApplicationUserGroup(app_code=application.code, role=group['role'], user_group_id=group['id'])
            for group in user_groups
        ]
    )

    # 4. 为默认的三个用户组授权
    cli.grant_user_group_policies(application.code, application.name, user_groups)

    # 5. 将创建者添加到管理者用户组，返回数据中第一个即为管理者用户组信息
    cli.add_user_group_members(user_groups[0]['id'], [creator], NEVER_EXPIRE_DAYS)
