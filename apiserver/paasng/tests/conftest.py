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

import atexit
import logging
import urllib.parse
from contextlib import suppress
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Union

import MySQLdb
import pytest
import sqlalchemy as sa
from blue_krill.monitoring.probe.mysql import transfer_django_db_settings
from django.conf import settings
from django.core.management import call_command
from django.db import transaction
from django.test.utils import override_settings
from django_dynamic_fixture import G
from filelock import FileLock
from rest_framework.test import APIClient
from sqlalchemy.orm import scoped_session, sessionmaker

from paas_wl.infras.cluster.models import Cluster
from paas_wl.workloads.networking.entrance.addrs import Address, AddressType
from paasng.accessories.publish.sync_market.handlers import (
    before_finishing_application_creation,
    register_app_core_data,
)
from paasng.accessories.publish.sync_market.managers import AppManger
from paasng.bk_plugins.bk_plugins.models import BkPluginProfile
from paasng.core.core.storages.sqlalchemy import console_db, legacy_db
from paasng.core.core.storages.utils import SADBManager
from paasng.infras.accounts.constants import SiteRole
from paasng.infras.accounts.models import UserProfile
from paasng.platform.applications.constants import ApplicationRole
from paasng.platform.applications.handlers import post_create_application, turn_on_bk_log_feature_for_app
from paasng.platform.applications.models import Application, ModuleEnvironment
from paasng.platform.applications.utils import create_default_module
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.manager import make_app_metadata as make_app_metadata_stub
from paasng.platform.modules.models.module import Module
from paasng.platform.sourcectl.models import SourceTypeSpecConfig
from paasng.platform.sourcectl.source_types import refresh_sourcectl_types
from paasng.platform.sourcectl.svn.client import LocalClient, RemoteClient, RepoProvider
from paasng.platform.sourcectl.utils import generate_temp_dir
from paasng.utils.blobstore import S3Store, make_blob_store
from tests.paasng.platform.engine.setup_utils import create_fake_deployment
from tests.utils import mock
from tests.utils.auth import create_user
from tests.utils.cluster import CLUSTER_NAME_FOR_TESTING, build_default_cluster
from tests.utils.helpers import (
    _mock_wl_services_in_creation,
    configure_regions,
    create_app,
    create_cnative_app,
    create_pending_wl_apps,
    generate_random_string,
    initialize_module,
)

# Install auto-used fixture
from tests.utils.mocks.cluster import _cluster_service_allow_nonexisting_wl_apps  # noqa: F401

logger = logging.getLogger(__name__)

# The default region for testing
DEFAULT_REGION = settings.DEFAULT_REGION_NAME

svn_lock_fn = Path(__file__).parent / ".svn"
atexit.register(lambda: svn_lock_fn.unlink(missing_ok=True))


def pytest_addoption(parser):
    parser.addoption(
        "--init-test-app-repo",
        dest="init_test_app_repo",
        action="store_true",
        default=False,
        help="是否需要执行测试应用的初始化流程(svn repo)",
    )
    parser.addoption(
        "--init-s3-bucket",
        dest="init_s3_bucket",
        action="store_true",
        default=False,
        help="是否需要执行 s3 初始化流程",
    )
    parser.addoption(
        "--run-e2e-test", dest="run_e2e_test", action="store_true", default=False, help="是否执行 e2e 测试"
    )


@pytest.fixture(autouse=True, scope="session")
def _configure_default_region():
    with configure_regions([DEFAULT_REGION]):
        yield


@pytest.fixture(autouse=True, scope="session")
def _drop_legacy_db(request, django_db_keepdb: bool):
    """在单元测试结束后, 自动摧毁测试数据库, 除非用户显式要求保留"""
    if django_db_keepdb:
        return

    @request.addfinalizer
    def drop_legacy_db_core():
        mysql_config = asdict(transfer_django_db_settings(settings.PAAS_LEGACY_DBCONF))
        db = mysql_config.pop("database")
        connection = MySQLdb.connect(charset="utf8", **mysql_config)
        with suppress(Exception), connection.cursor() as cursor:
            cursor.execute(f"drop database {db}")


@pytest.fixture(autouse=True, scope="session")
def _configure_docker_registry_config():
    with override_settings(
        DOCKER_REGISTRY_CONFIG={"DEFAULT_REGISTRY": "127.0.0.1:5000", "ALLOW_THIRD_PARTY_REGISTRY": False}
    ):
        yield


@pytest.fixture(autouse=True, scope="session")
def _configure_remote_service():
    # unittest should not configure any remote service endpoints
    with override_settings(SERVICE_REMOTE_ENDPOINTS=None):
        yield


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):  # noqa: PT004
    """Create the default cluster for testing."""

    with django_db_blocker.unblock(), transaction.atomic():
        Cluster.objects.all().delete()
        cluster, apiserver = build_default_cluster()
        cluster.save()
        apiserver.save()


def pytest_sessionstart(session):
    """Called before running all tests:

    - Reset `make_app_metadata` function to avoid calling PaaS-Analysis service
    """
    # Create required buckets if not exists
    from django.conf import settings

    from paasng.utils.blobstore import get_storage_by_bucket

    get_storage_by_bucket("engine-ng")
    get_storage_by_bucket("paas-v3-package")
    get_storage_by_bucket(settings.SERVICE_LOGO_BUCKET)
    get_storage_by_bucket(settings.APP_LOGO_BUCKET)


@pytest.fixture()
def legacy_app_code():
    """The legacy App code using for Unit test"""
    return getattr(settings, "FOR_TESTS_LEGACY_APP_CODE", "document")


@pytest.fixture(autouse=True)
def _auto_init_legacy_app(request):
    if "legacy_app_code" not in request.fixturenames:
        yield
        return

    legacy_app_code = request.getfixturevalue("legacy_app_code")
    call_command("make_legacy_app_for_test", f"--code={legacy_app_code}", "--username=nobody", "--silence")

    yield

    # Clean the legacy app data after test
    with legacy_db.session_scope() as session:
        AppManger(session).delete_by_code(legacy_app_code)


@pytest.fixture(autouse=True, scope="session")
def _skip_iam_migrations():
    with override_settings(BK_IAM_SKIP=True):
        yield


@pytest.fixture(autouse=True)
def _skip_bk_audit_add_event():
    with override_settings(ENABLE_BK_AUDIT=False):
        yield


@pytest.fixture(autouse=True)
def _sqlalchemy_transaction(request):
    """为使用了 sqlalchemy 操作 legacy db 的单元测试提供自动回滚，保证单元测试前后的状态一致"""
    session = None

    def fake_sessionmaker(*args, **kwargs):
        # copy from [pytest_flask_sqlalchemy](https://github.com/jeancochrane/pytest-flask-sqlalchemy/blob/master/pytest_flask_sqlalchemy/fixtures.py)
        # but remove flask requirement
        nonlocal session
        if session is not None:
            # 由于要控制 session 的 rollback, 需确保在scope=`function`的范围内, 只有一个 session 实例
            return session

        # TODO: 直接 patch SqlalchemyDBManager 对象
        if not check_legacy_enabled():
            raise pytest.skip("Legacy db engine is not initialized")

        engine = legacy_db.engine
        connection = engine.connect()
        transaction = connection.begin()
        session = scoped_session(sessionmaker(bind=connection, expire_on_commit=False))

        # Make sure the session, connection, and transaction can't be closed by accident in
        # the codebase
        connection.force_close = connection.close
        transaction.force_rollback = transaction.rollback

        connection.close = lambda: None
        transaction.rollback = lambda: None
        session.close = lambda: None

        # Begin a nested transaction (any new transactions created in the codebase
        # will be held until this outer transaction is committed or closed)
        session.begin_nested()

        # Each time the SAVEPOINT for the nested transaction ends, reopen it
        @sa.event.listens_for(session, "after_transaction_end")
        def restart_savepoint(session, trans):
            if trans.nested and not trans._parent.nested:
                # ensure that state is expired the way
                # session.commit() at the top level normally does
                session.expire_all()

                session.begin_nested()

        # Force the connection to use nested transactions
        connection.begin = connection.begin_nested

        # If an object gets moved to the 'detached' state by a call to flush the session,
        # add it back into the session (this allows us to see changes made to objects
        # in the context of a test, even when the change was made elsewhere in
        # the codebase)
        @sa.event.listens_for(session, "persistent_to_detached")
        @sa.event.listens_for(session, "deleted_to_detached")
        def rehydrate_object(session, obj):
            session.add(obj)

        @request.addfinalizer
        def teardown_transaction():
            # Delete the session
            session.remove()  # type: ignore

            # Rollback the transaction and return the connection to the pool
            transaction.force_rollback()
            connection.force_close()

        return session

    with mock.patch.object(legacy_db, "get_scoped_session") as _sessionmaker:
        _sessionmaker.side_effect = fake_sessionmaker
        yield


@pytest.fixture(autouse=True, scope="session")
def _init_test_app_repo(request):
    """初始化测试应用仓库"""
    if not request.config.getvalue("init_test_app_repo"):
        return

    try:
        repo_config = settings.FOR_TESTS_SVN_SERVER_CONF
    except Exception:
        return

    # use filelock to ensure svn initial will only run once
    with FileLock(str(svn_lock_fn) + ".lock"):
        if svn_lock_fn.exists():
            return
        svn_lock_fn.write_text("")

    provider = RepoProvider(
        base_url=repo_config["base_url"], username=repo_config["su_name"], password=repo_config["su_pass"]
    )
    ret = provider.provision(settings.FOR_TESTS_LEGACY_APP_CODE)
    repo_url = ret["repo_url"] + "/"

    rclient = RemoteClient(
        urllib.parse.urljoin(repo_url, "trunk/"), username=repo_config["su_name"], password=repo_config["su_pass"]
    )
    with generate_temp_dir() as working_dir:
        # step 1. checkout
        rclient.checkout(working_dir)
        procfile_path = working_dir / "Procfile"
        # step 2. 创建 Procfile
        procfile_path.write_text("web: echo 'test'")
        # ste[ 3. 推送 Procfile 至服务器
        lclient = LocalClient(working_dir, username=repo_config["su_name"], password=repo_config["su_pass"])
        if not procfile_path.exists():
            lclient.add(str(procfile_path))
        else:
            lclient.update(str(procfile_path))
        lclient.commit("for test", rel_filepaths=[working_dir])


@pytest.fixture(autouse=True, scope="session")
def _init_s3_bucket(request):
    if not request.config.getvalue("init_s3_bucket"):
        return

    for bucket in [
        settings.BLOBSTORE_BUCKET_APP_SOURCE,
        settings.BLOBSTORE_BUCKET_TEMPLATES,
        settings.BLOBSTORE_BUCKET_AP_PACKAGES,
    ]:
        store = make_blob_store(bucket)
        if not isinstance(store, S3Store):
            continue

        with suppress(Exception):
            store.get_client().Bucket(bucket).create()


@pytest.fixture(autouse=True, scope="session")
def _override_make_app_metadata():
    old_handler = make_app_metadata_stub.handler
    make_app_metadata_stub.use(lambda env: {}, force_replace=True)
    yield
    if old_handler:
        make_app_metadata_stub.use(old_handler, force_replace=True)


@pytest.fixture()
def random_name():
    """Generate an random name which can be used for app's code & name"""
    return "ut{}".format(generate_random_string(length=6))


@pytest.fixture()
def bk_user(request):
    """Generate a random user"""
    user = create_user()
    return user


@pytest.fixture(autouse=True)
def _mock_iam():
    def mock_user_has_app_action_perm(user, application, action) -> bool:
        from paasng.infras.iam.constants import APP_DEFAULT_ROLES
        from paasng.infras.iam.helpers import fetch_user_roles
        from paasng.infras.iam.utils import get_app_actions_by_role
        from paasng.utils.basic import get_username_by_bkpaas_user_id

        user_roles = fetch_user_roles(application.code, get_username_by_bkpaas_user_id(user.pk))
        return any(role in user_roles and action in get_app_actions_by_role(role) for role in APP_DEFAULT_ROLES)

    from tests.utils.mocks.iam import StubBKIAMClient
    from tests.utils.mocks.permissions import StubApplicationPermission

    with mock.patch("paasng.infras.iam.client.BKIAMClient", new=StubBKIAMClient), mock.patch(
        "paasng.infras.iam.helpers.BKIAMClient",
        new=StubBKIAMClient,
    ), mock.patch(
        "paasng.platform.applications.helpers.BKIAMClient",
        new=StubBKIAMClient,
    ), mock.patch(
        "paasng.infras.iam.helpers.IAM_CLI",
        new=StubBKIAMClient(),
    ), mock.patch(
        "paasng.infras.accounts.permissions.application.user_has_app_action_perm",
        new=mock_user_has_app_action_perm,
    ), mock.patch(
        "paasng.platform.declarative.application.controller.user_has_app_action_perm",
        new=mock_user_has_app_action_perm,
    ), mock.patch(
        "paasng.platform.applications.models.ApplicationPermission",
        new=StubApplicationPermission,
    ), mock.patch(
        "paasng.plat_admin.numbers.app.ApplicationPermission",
        new=StubApplicationPermission,
    ):
        yield


@pytest.fixture(autouse=True)
def _mock_after_created_action():
    # skip registry app core data to console
    before_finishing_application_creation.disconnect(register_app_core_data)
    # skip turn on bk log feature by default because it required workloads database
    post_create_application.disconnect(turn_on_bk_log_feature_for_app)
    yield
    before_finishing_application_creation.connect(register_app_core_data)
    post_create_application.connect(turn_on_bk_log_feature_for_app)


@pytest.fixture()
def _turn_on_bk_log_feature_for_app():
    post_create_application.connect(turn_on_bk_log_feature_for_app)
    yield
    post_create_application.disconnect(turn_on_bk_log_feature_for_app)


@pytest.fixture()
def _register_app_core_data():
    before_finishing_application_creation.connect(register_app_core_data)
    yield
    before_finishing_application_creation.disconnect(register_app_core_data)


@pytest.fixture()
def bk_app(request, bk_user) -> Application:
    """Generate a random application owned by current user fixture

    This result object is not fully functional in order to speed up fixture, if you want a full featured applicƒsation.
    use `bk_app_full` instead.
    """
    return create_app(owner_username=bk_user.username)


@pytest.fixture()
def bk_cnative_app(request, bk_user):
    """Generate a random cloud-native application owned by current user fixture"""
    return create_cnative_app(owner_username=bk_user.username, cluster_name=CLUSTER_NAME_FOR_TESTING)


@pytest.fixture()
def bk_plugin_app(bk_app):
    bk_app.is_plugin_app = True
    bk_app.save(update_fields=["is_plugin_app"])

    # Create the related profile object
    BkPluginProfile.objects.get_or_create_by_application(bk_app)
    return bk_app


@pytest.fixture()
def bk_app_full(request, bk_user) -> Application:
    """Generate a random *fully featured* application owned by current user fixture"""
    return create_app(owner_username=bk_user.username, additional_modules=["deploy_phases", "sourcectl"])


@pytest.fixture()
def bk_module(request) -> Module:
    """Return the default module if current application fixture"""
    if "bk_cnative_app" in request.fixturenames:
        bk_app = request.getfixturevalue("bk_cnative_app")
    else:
        bk_app = request.getfixturevalue("bk_app")
    return bk_app.get_default_module()


@pytest.fixture()
def bk_module_full(request) -> Module:
    """Return the *fully featured* default module"""
    if "bk_cnative_app" in request.fixturenames:
        bk_app = request.getfixturevalue("bk_cnative_app")
    else:
        bk_app = request.getfixturevalue("bk_app_full")
    return bk_app.get_default_module()


@pytest.fixture()
def bk_stag_env(request, bk_module) -> ModuleEnvironment:
    return bk_module.envs.get(environment="stag")


@pytest.fixture()
def bk_prod_env(request, bk_module) -> ModuleEnvironment:
    return bk_module.envs.get(environment="prod")


@pytest.fixture()
def bk_env(request):
    if request.param is None:
        return None
    return request.getfixturevalue(request.param)


@pytest.fixture()
def bk_deployment(bk_module):
    """Generate a simple deployment object"""
    return create_fake_deployment(bk_module)


@pytest.fixture()
def bk_deployment_full(bk_module_full):
    """Generate a simple deployment object for bk_module_full(which have source_obj)"""
    return create_fake_deployment(bk_module_full)


@pytest.fixture()
def api_client(request, bk_user):
    """Return an authenticated client"""
    client = APIClient()
    client.force_authenticate(user=bk_user)
    return client


@pytest.fixture()
def sys_api_client(bk_user):
    """Return an authenticated client which has an authenticated user with system API permissions"""
    client = APIClient()
    client.force_authenticate(user=bk_user)
    # Update user permission
    UserProfile.objects.update_or_create(
        user=bk_user.pk, defaults={"role": SiteRole.SYSTEM_API_BASIC_MAINTAINER.value}
    )
    return client


@pytest.fixture()
def sys_light_api_client(bk_user):
    """Return an authenticated client which has an authenticated user with Light App permissions"""
    client = APIClient()
    client.force_authenticate(user=bk_user)
    # Update user permission
    UserProfile.objects.update_or_create(
        user=bk_user.pk, defaults={"role": SiteRole.SYSTEM_API_LIGHT_APP_MAINTAINER.value}
    )
    return client


@pytest.fixture()
def sys_lesscode_api_client(bk_user):
    """Return an authenticated client which has an authenticated user with Lesscode permissions"""
    client = APIClient()
    client.force_authenticate(user=bk_user)
    # Update user permission
    UserProfile.objects.update_or_create(user=bk_user.pk, defaults={"role": SiteRole.SYSTEM_API_LESSCODE.value})
    return client


@pytest.fixture()
def svn_repo_credentials():
    conf = getattr(settings, "FOR_TESTS_APP_SVN_INFO", None)
    if not conf:
        pytest.skip("local svn config and app repo path is not defined in settings")
    return conf


@pytest.fixture()
def dummy_svn_spec():
    """Local Svn address for running unittest"""
    return {
        "spec_cls": "paasng.platform.sourcectl.type_specs.BkSvnSourceTypeSpec",
        "attrs": {
            "name": "dft_bk_svn",
            "server_config": {
                "base_url": "svn://127.0.0.1:3790/apps/",
                "legacy_base_url": "svn://127.0.0.1:3790/l-apps/",
                "su_name": "test-username",
                "su_pass": "test-password",
                "need_security": False,
                "admin_url": "127.0.0.1:3790",
                "auth_mgr_cls": "paasng.platform.sourcectl.svn.admin.DummyAppAuthorization",
            },
        },
    }


@pytest.fixture()
def dummy_gitlab_spec():
    """Local GitLab address for running unittest"""
    return {
        "spec_cls": "paasng.platform.sourcectl.type_specs.GitLabSourceTypeSpec",
        "attrs": {
            "name": "dft_gitlab",
            "server_config": {"api_url": "http://127.0.0.1:8080/"},
            "oauth_credentials": {
                "client_id": "client_id",
                "client_secret": "client_secret",
                "authorization_base_url": "http://127.0.0.1:8080/owner/repo.git",
                "token_base_url": "https://127.0.0.1:8080/",
                "redirect_uri": "https://127.0.0.1:8080/",
            },
        },
    }


@pytest.fixture(autouse=True)
def _setup_default_sourcectl_types(dummy_svn_spec, dummy_gitlab_spec):
    spec_cls_module_path = "paasng.platform.sourcectl.type_specs"

    dummy_oauth_config = {
        "client_id": "dummy_client_id",
        "client_secret": "dummy_client_secret",
        "authorization_base_url": "http://127.0.0.1:8080/owner/repo.git",
        "token_base_url": "https://127.0.0.1:8080/",
        "redirect_uri": "https://127.0.0.1:8080/",
    }

    configs = [
        SourceTypeSpecConfig(
            name="bare_svn",
            label_zh_cn="bare_svn",
            label_en="bare_svn",
            enabled=True,
            spec_cls=f"{spec_cls_module_path}.BareSvnSourceTypeSpec",
        ),
        SourceTypeSpecConfig(
            name="bare_git",
            label_zh_cn="bare_git",
            label_en="bare_git",
            enabled=True,
            spec_cls=f"{spec_cls_module_path}.BareGitSourceTypeSpec",
        ),
        SourceTypeSpecConfig(
            name="github",
            label_zh_cn="github",
            label_en="github",
            enabled=True,
            spec_cls=f"{spec_cls_module_path}.GitHubSourceTypeSpec",
            server_config={"api_url": "https://api.github.com/"},
            **dummy_oauth_config,
        ),
        SourceTypeSpecConfig(
            name="gitee",
            label_zh_cn="gitee",
            label_en="gitee",
            enabled=True,
            spec_cls=f"{spec_cls_module_path}.GiteeSourceTypeSpec",
            server_config={"api_url": "https://gitee.com/api/v5/"},
            **dummy_oauth_config,
        ),
    ]

    type_configs = [dummy_gitlab_spec, dummy_svn_spec]
    type_configs.extend([c.to_dict() for c in configs])
    refresh_sourcectl_types(type_configs)


@pytest.fixture()
def _init_tmpls():
    from paasng.platform.engine.constants import RuntimeType
    from paasng.platform.templates.constants import TemplateType
    from paasng.platform.templates.models import Template

    Template.objects.get_or_create(
        name=settings.DUMMY_TEMPLATE_NAME,
        defaults={
            "type": TemplateType.NORMAL,
            "display_name_zh_cn": "测试用模板",
            "display_name_en": "dummy_template",
            "description_zh_cn": "测试用模板描述",
            "description_en": "dummy_template_desc",
            "language": "Python",
            "market_ready": True,
            "preset_services_config": {"mysql": {}},
            "blob_url": {settings.DEFAULT_REGION_NAME: f"file:{settings.BASE_DIR}/tests/contents/dummy-tmpl.tar.gz"},
            "enabled_regions": [settings.DEFAULT_REGION_NAME],
            "required_buildpacks": [],
            "processes": {"web": "python manage.py runserver"},
            "tags": [],
            "repo_url": "http://github.com/blueking/dummy_tmpl",
        },
    )

    Template.objects.get_or_create(
        name="php_legacy",
        defaults={
            "type": TemplateType.NORMAL,
            "display_name_zh_cn": "旧版本 PHP 应用迁移",
            "display_name_en": "legacy php app migrate",
            "description_zh_cn": "旧版本 PHP 应用迁移",
            "description_en": "legacy php app migrate desc",
            "language": "PHP",
            "market_ready": True,
            "preset_services_config": {},
            "blob_url": {settings.DEFAULT_REGION_NAME: f"file:{settings.BASE_DIR}/tests/contents/dummy-tmpl.tar.gz"},
            "enabled_regions": [settings.DEFAULT_REGION_NAME],
            "required_buildpacks": [],
            "processes": {},
            "tags": [],
            "repo_url": "http://github.com/blueking/php_legacy_tmpl",
        },
    )

    Template.objects.get_or_create(
        name="django_legacy",
        defaults={
            "type": TemplateType.NORMAL,
            "display_name_zh_cn": "旧版本 Django 应用迁移",
            "display_name_en": "legacy django app migrate",
            "description_zh_cn": "旧版本 Django 应用迁移",
            "description_en": "legacy django app migrate desc",
            "language": "Python",
            "market_ready": True,
            "preset_services_config": {},
            "blob_url": {settings.DEFAULT_REGION_NAME: f"file:{settings.BASE_DIR}/tests/contents/dummy-tmpl.tar.gz"},
            "enabled_regions": [settings.DEFAULT_REGION_NAME],
            "required_buildpacks": [],
            "processes": {},
            "tags": [],
            "repo_url": "http://github.com/blueking/django_legacy_tmpl",
        },
    )

    Template.objects.get_or_create(
        name="docker",
        defaults={
            "type": TemplateType.NORMAL,
            "display_name_zh_cn": "Docker应用模板",
            "display_name_en": "Docker app template",
            "description_zh_cn": "Docker应用模板",
            "description_en": "Docker app template",
            "market_ready": True,
            "preset_services_config": {},
            "blob_url": {settings.DEFAULT_REGION_NAME: f"file:{settings.BASE_DIR}/tests/contents/dummy-tmpl.tar.gz"},
            "enabled_regions": [settings.DEFAULT_REGION_NAME],
            "required_buildpacks": [],
            "processes": {},
            "tags": [],
            "runtime_type": RuntimeType.DOCKERFILE,
        },
    )
    Template.objects.get_or_create(
        name="bk-saas-plugin-python",
        defaults={
            "type": TemplateType.PLUGIN,
            "display_name_zh_cn": "Python 语言",
            "display_name_en": "Python",
            "description_zh_cn": "Python + bk-plugin-framework，集成插件开发框架，插件版本管理，插件运行时等模块",
            "description_en": "Integrate plugin development framework, plugin version management, and plugin runtime modules.",
            "language": "Python",
            "market_ready": False,
            "preset_services_config": {"mysql": {}},
            "blob_url": {},
            "enabled_regions": [settings.DEFAULT_REGION_NAME],
            "required_buildpacks": [],
            "processes": {},
            "tags": [],
            "runtime_type": RuntimeType.BUILDPACK,
        },
    )
    Template.objects.get_or_create(
        name="bk-saas-plugin-go",
        defaults={
            "type": TemplateType.PLUGIN,
            "display_name_zh_cn": "Go 语言",
            "display_name_en": "Go",
            "description_zh_cn": "Go + bk-plugin-framework，集成插件开发框架，插件版本管理，插件运行时等模块",
            "description_en": "Integrate Go development framework, plugin version management, and plugin runtime modules.",
            "language": "Go",
            "market_ready": False,
            "preset_services_config": {"mysql": {}},
            "blob_url": {},
            "enabled_regions": [settings.DEFAULT_REGION_NAME],
            "required_buildpacks": [],
            "processes": {},
            "tags": [],
            "runtime_type": RuntimeType.BUILDPACK,
        },
    )


@pytest.fixture()
def create_custom_app():
    def create(owner, **kwargs):
        random_name = generate_random_string(length=6)
        region = kwargs.get("region", "ieod")
        application = G(
            Application,
            owner=owner.pk,
            code=kwargs.get("code", random_name),
            name=kwargs.get("name", random_name),
            language=kwargs.get("language", "Python"),
            region=region,
        )

        if "init_default_module" in kwargs:
            create_default_module(application, source_origin=kwargs.get("source_origin", SourceOrigin.BK_LESS_CODE))

        from tests.utils.helpers import register_iam_after_create_application

        register_iam_after_create_application(application)

        # 添加开发者
        from paasng.infras.iam.helpers import add_role_members

        if "developers" in kwargs and isinstance(kwargs["developers"], list):
            add_role_members(application.code, ApplicationRole.DEVELOPER, kwargs["developers"])
        # 添加运营者
        if "ops" in kwargs and isinstance(kwargs["ops"], list):
            add_role_members(application.code, ApplicationRole.OPERATOR, kwargs["ops"])

        return application

    return create


@pytest.fixture()
def bk_module_2(bk_app):
    """Another module other than the default one, for testing."""
    module = Module.objects.create(region=bk_app.region, application=bk_app, name=generate_random_string(length=8))
    initialize_module(module)
    return module


# Mocking fixtures


def _mock_paas_analysis_client():
    try:
        with mock.patch("paasng.accessories.paas_analysis.clients.PAClient") as mocked_client:
            mocked_client().get_or_create_app_site.return_value = dict(type="app", id="id", name="name")
            yield mocked_client()
    except ModuleNotFoundError:
        # Module 'paasng.accessories.paas_analysis' not found in current edition, skip mocking
        yield


mock_paas_analysis_client = pytest.fixture(_mock_paas_analysis_client)
mock_wl_services_in_creation = pytest.fixture(_mock_wl_services_in_creation)


def check_legacy_enabled():
    """check if legacy database was configured properly"""
    return isinstance(legacy_db, SADBManager)


def skip_if_legacy_not_configured():
    """Return a pytest mark to skip tests when legacy database was not configured"""
    return pytest.mark.skipif(not check_legacy_enabled(), reason="Legacy db engine is not initialized")


def check_console_enabled():
    """check if console database was configured properly"""
    return isinstance(console_db, SADBManager)


def mark_skip_if_console_not_configured():
    """Return a pytest mark to skip tests when console database was not configured"""
    return pytest.mark.skipif(not check_console_enabled(), reason="Console db engine is not initialized")


@pytest.fixture()
def mock_env_is_running():
    status: Dict[Union[str, ModuleEnvironment], bool] = {}

    def side_effect(env: ModuleEnvironment) -> bool:
        if env in status:
            return status[env]
        return status.get(env.environment, False)

    status["side_effect"] = side_effect  # type: ignore
    with mock.patch("paasng.accessories.publish.entrance.exposer.env_is_running") as m1, mock.patch(
        "paas_wl.workloads.networking.entrance.shim.env_is_running"
    ) as m2:
        m1.side_effect = side_effect
        m2.side_effect = side_effect
        yield status


@pytest.fixture()
def mock_get_builtin_addresses(mock_env_is_running):
    addresses: Dict[str, List] = {}

    def side_effect(env: ModuleEnvironment) -> tuple:
        env_is_running = mock_env_is_running["side_effect"](env)
        if env in addresses:
            return env_is_running, addresses[env]
        return env_is_running, addresses.get(env.environment, [])

    with mock.patch("paas_wl.workloads.networking.entrance.shim.get_builtin_addrs") as m:
        m.side_effect = side_effect
        yield addresses


@pytest.fixture()
def _with_empty_live_addrs(mock_env_is_running, mock_get_builtin_addresses):
    """Always return empty addresses by patching `get_builtin_addresses` function"""
    return


@pytest.fixture()
def _with_live_addrs(mock_env_is_running, mock_get_builtin_addresses):
    """Always return valid addresses by patching `get_builtin_addresses` function"""
    mock_env_is_running["stag"] = True
    mock_env_is_running["prod"] = True
    mock_get_builtin_addresses["stag"] = [
        Address(type=AddressType.SUBPATH, url="http://example.com/foo-stag/"),
        Address(type=AddressType.SUBDOMAIN, url="http://foo-stag.example.com"),
    ]
    mock_get_builtin_addresses["prod"] = [
        Address(type=AddressType.SUBPATH, url="http://example.com/foo-prod/"),
        Address(type=AddressType.SUBDOMAIN, url="http://foo-prod.example.com"),
    ]


@pytest.fixture()
def _with_wl_apps(request):
    """Create all pending WlApp objects related with current bk_app, useful
    for tests which want to use `bk_app`, `bk_stag_env` fixtures.
    """
    if "bk_cnative_app" in request.fixturenames:
        bk_app = request.getfixturevalue("bk_cnative_app")
    else:
        bk_app = request.getfixturevalue("bk_app")

    create_pending_wl_apps(bk_app, cluster_name=CLUSTER_NAME_FOR_TESTING)


@pytest.fixture(autouse=True, scope="session")
def _mock_sync_developers_to_sentry():
    # 避免单元测试时会往 celery 推送任务
    with mock.patch("paasng.platform.applications.views.sync_developers_to_sentry"), mock.patch(
        "paasng.bk_plugins.bk_plugins.pluginscenter_views.sync_developers_to_sentry"
    ):
        yield


@pytest.fixture(autouse=True, scope="session")
def _mock_delete_process_probe(request):
    skip_patch = request.param if hasattr(request, "param") else False

    if not skip_patch:
        # 避免所有单元测试会执行删除 ProcessProbe 操作
        with mock.patch("paasng.platform.declarative.deployment.controller.delete_process_probes"):
            yield
    else:
        yield
