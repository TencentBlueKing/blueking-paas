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
import logging

import pytest
from django_dynamic_fixture import G

from paasng.accessories.iam.helpers import add_role_members, delete_role_members
from paasng.engine.constants import JobStatus
from paasng.engine.models.deployment import Deployment
from paasng.platform.applications.constants import ApplicationRole
from paasng.platform.applications.exceptions import AppFieldValidationError, IntegrityError
from paasng.platform.core.storages.sqlalchemy import console_db
from paasng.platform.mgrlegacy.constants import LegacyAppState
from paasng.publish.market.models import Product
from paasng.publish.sync_market.handlers import (
    on_change_application_name,
    on_product_deploy_success,
    register_app_core_data,
    register_application_with_default,
    sync_console_app_developers,
    sync_console_app_devopses,
    sync_release_record,
    validate_app_code_uniquely,
    validate_app_name_uniquely,
)
from paasng.publish.sync_market.managers import AppDeveloperManger, AppManger, AppOpsManger, AppReleaseRecordManger
from tests.conftest import mark_skip_if_console_not_configured
from tests.utils.helpers import create_app, generate_random_string

pytestmark = [mark_skip_if_console_not_configured(), pytest.mark.django_db]


logger = logging.getLogger(__name__)


class TestAppMembers:
    @pytest.fixture(autouse=True)
    def init_data(self, bk_user, create_custom_app):
        init_users = [bk_user.username, 'user1', 'user2', 'user3']
        app = create_custom_app(bk_user, developers=init_users, ops=init_users)
        # 创建应用后，将应用注册到 console
        register_application_with_default(app.region, app.code, app.name)
        return app, init_users

    def test_init_members(self, init_data):
        app, init_users = init_data

        # 验证桌面保存的开发者信息是否一致
        session = console_db.get_scoped_session()
        assert set(AppDeveloperManger(session).get_developer_names(app.code)) == set(init_users)
        try:
            assert set(AppOpsManger(session).get_ops_names(app.code)) == set(init_users)
        except NotImplementedError:
            logger.warning('AppOpsManger get_ops_names not implemented , skip')

    def test_delete_members(self, init_data):
        app, init_users = init_data
        # 删除成员
        delete_user = 'user1'
        sync_users = set(init_users)
        sync_users.remove(delete_user)

        # 删除开发者与运营者
        delete_role_members(app.code, ApplicationRole.DEVELOPER, delete_user)
        delete_role_members(app.code, ApplicationRole.OPERATOR, delete_user)

        with console_db.session_scope() as session:
            # 删除后同步到桌面
            sync_console_app_developers(app, session)
            sync_console_app_devopses(app, session)
            assert set(AppDeveloperManger(session).get_developer_names(app.code)) == sync_users
            try:
                assert set(AppOpsManger(session).get_ops_names(app.code)) == sync_users
            except NotImplementedError:
                logger.warning('AppOpsManger get_ops_names not implemented , skip')

    def test_add_members(self, init_data):
        app, init_users = init_data
        # 添加成员
        add_user = 'user4'
        sync_users = set(init_users)
        sync_users.add(add_user)
        # 将用户添加为开发者，运营者
        add_role_members(app.code, ApplicationRole.DEVELOPER, add_user)
        add_role_members(app.code, ApplicationRole.OPERATOR, add_user)

        with console_db.session_scope() as session:
            # 添加后后同步到桌面
            sync_console_app_developers(app, session)
            sync_console_app_devopses(app, session)
            assert set(AppDeveloperManger(session).get_developer_names(app.code)) == sync_users
            try:
                assert set(AppOpsManger(session).get_ops_names(app.code)) == sync_users
            except NotImplementedError:
                logger.warning('AppOpsManger get_ops_names not implemented , skip')


class TestApp:
    """
    部分功能的单元测试已经包含在其他模块
    - 同步应用信息：tests/api/test_market.py::TestGetAndUpdateProduct
    """

    def test_validate_app_code(self, bk_app):
        # with pytest.raises(AppFieldValidationError):
        try:
            validate_app_code_uniquely(self, bk_app.code)
        except Exception as e:
            print(e)

    def test_validate_app_name(self, bk_app):
        new_app = create_app()
        with pytest.raises(AppFieldValidationError):
            validate_app_name_uniquely(self, bk_app.name, new_app)

    def test_change_app_name(self, bk_app):
        new_app = create_app()
        # 修改应用名称冲突
        with pytest.raises(IntegrityError):
            on_change_application_name(self, new_app.code, bk_app.name)
        # 修改一个不存在应用的名称
        with pytest.raises(AppFieldValidationError):
            on_change_application_name(self, new_app.code + '2', bk_app.name)
        # 修改名称成功
        new_name = generate_random_string(10)
        on_change_application_name(self, new_app.code, new_name)
        session = console_db.get_scoped_session()
        app = AppManger(session).get(new_app.code)
        assert app.name == new_name

    def test_register_app(self, bk_app):
        # 再次手动注册会异常
        with pytest.raises(IntegrityError):
            register_app_core_data(self, bk_app)

    def test_app_state(self, bk_user, create_custom_app):
        app = create_custom_app(bk_user)
        app = register_application_with_default(app.region, app.code, app.name)
        # 默认创建的应用未开发状态，不能同步显示到桌面
        assert app.state == LegacyAppState.DEVELOPMENT.value
        assert app.is_already_test == 0
        assert app.is_already_online == 0


def test_create_release_record(bk_app):
    with console_db.session_scope() as session:
        AppReleaseRecordManger(session).create(bk_app.code, 'userfoo', 'prod')


class TestHandlers:
    def test_sync_app_deploy_records(self, bk_prod_env):
        deployment = G(Deployment, app_environment=bk_prod_env, status=JobStatus.SUCCESSFUL.value)
        sync_release_record(bk_prod_env, deployment)


class TestProduct:
    def test_create_default_product(self, bk_app, create_default_tag):
        product = Product.objects.create_default_product(bk_app)
        assert product == bk_app.get_product()
        assert product.tag is not None

        # 将应用部署到生产环境
        on_product_deploy_success(product, 'prod')
        # 验证应用上线信息是否已经同步到桌面
        with console_db.session_scope() as session:
            console_app = AppManger(session).get(bk_app.code)
            assert console_app.is_already_online == 1
            assert console_app.open_mode == "new_tab"
