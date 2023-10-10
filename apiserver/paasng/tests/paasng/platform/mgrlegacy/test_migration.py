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
from typing import List, Type

import pytest
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase

from paasng.infras.iam.helpers import fetch_application_members
from paasng.platform.sourcectl.models import SvnRepository
from paasng.platform.mgrlegacy.app_migrations.basic import BaseMigration, BaseObjectMigration, MainInfoMigration
from paasng.platform.mgrlegacy.app_migrations.product import ProductMigration
from paasng.platform.mgrlegacy.exceptions import MigrationFailed
from paasng.platform.mgrlegacy.models import MigrationContext
from paasng.platform.modules.manager import ModuleInitializer
from paasng.accessories.publish.market.models import DisplayOptions, MarketConfig, Product
from tests.conftest import skip_if_legacy_not_configured
from tests.paasng.platform.mgrlegacy.utils import get_legacy_app, get_migration_instance, global_mock
from tests.utils import mock

try:
    from paasng.platform.mgrlegacy.app_migrations.sourcectl_te import SourceControlMigration
except ImportError:
    from paasng.platform.mgrlegacy.app_migrations.sourcectl import SourceControlMigration


pytestmark = skip_if_legacy_not_configured()


@pytest.mark.usefixtures("legacy_app_code")
class BaseTestCaseForMigration(TestCase):
    MIGRATION_CLS = BaseMigration
    PRECONDITION_MIGRATION_CLS: List[Type] = []

    def setUp(self) -> None:
        super().setUp()

        self.migration = get_migration_instance(self.MIGRATION_CLS)
        self.context: MigrationContext = self.migration.context
        self.pre_migrations = [cls(self.context) for cls in self.PRECONDITION_MIGRATION_CLS]

        with global_mock(self.context):
            for migration in self.pre_migrations:
                migration.migrate()
        # 绑定 migration_process 和 app, 如果不绑定, 会导致死锁
        if self.context.app is not None:
            self.context.migration_process.app = self.context.app
            self.context.migration_process.save()

    def tearDown(self) -> None:
        with global_mock(self.context):
            for migration in reversed(self.pre_migrations):
                migration.rollback()
        super().tearDown()


class TestBaseMigration(BaseTestCaseForMigration):
    MIGRATION_CLS = BaseMigration

    def setUp(self):
        super().setUp()
        self.migration.get_description = lambda: "BaseMigration"  # type: ignore

    def tearDown(self):
        super().tearDown()

    def test_set_log(self):
        # clear context.migration_process.ongoing_migration
        old_migration_info = self.migration.get_info()
        self.migration.set_log("test-set-log")
        new_migration_info = self.migration.get_info()
        assert old_migration_info != new_migration_info, "set_log 未修改 migration info"
        assert (
            self.context.migration_process.ongoing_migration == new_migration_info
        ), "set_log 未持久化 migration info 到 migration_process"

    def test_update_ongoing(self):
        # clear context.migration_process.ongoing_migration
        self.context.migration_process.ongoing_migration = "stub"
        self.context.migration_process.save(update_fields=['ongoing_migration'])
        assert self.context.migration_process.ongoing_migration == "stub", "修改数据失败"
        self.migration.update_ongoing()
        assert self.context.migration_process.ongoing_migration != "stub", "update_ongoing does not change ongoing"

    def test_add_log(self):
        self.migration.set_log("prefix")
        old_migration_info = self.migration.get_info()
        self.migration.add_log("-content")
        new_migration_info = self.migration.get_info()
        assert old_migration_info != new_migration_info, "add_log 未修改 migration info"
        assert old_migration_info.pop("log") != new_migration_info.pop("log"), "add_log 未修改 migration_info.log"
        assert old_migration_info == new_migration_info, "add_log 修改了 migration 除 log 以外的其他信息"

    def test_migrate_success(self):
        self.migration.migrate = lambda: "正常运行"  # type: ignore
        self.migration.apply_migration()
        assert self.migration.successful, "migrate raise exception"

    def test_migrate_exception(self):
        # simulate raise exception
        self.migration.migrate = mock.MagicMock(side_effect=RuntimeError)  # type: ignore
        with pytest.raises(MigrationFailed) as exc_info:
            self.migration.apply_migration()
        assert self.migration.successful is False, "apply_migration 未抛异常"
        assert self.migration.failed_reason in str(exc_info), "捕获异常信息未透传"

    def test_rollback_success(self):
        self.migration.rollback = lambda: "正常运行"  # type: ignore
        self.migration.apply_rollback()
        assert self.migration.apply_type == "rollback", "执行 apply_rollback 后, migration类型未改成 rollback"
        assert self.migration.successful, "执行 apply_rollback 失败但未报错"
        assert self.migration.finished, "执行 apply_rollback 后, migration 未标记为完成"

    def test_rollback_exception(self):
        # simulate raise exception
        self.migration.rollback = mock.MagicMock(side_effect=RuntimeError)  # type: ignore
        self.migration.apply_rollback()
        assert self.migration.apply_type == "rollback", "执行 apply_rollback 后, migration类型未改成 rollback"
        assert self.migration.successful is False, "执行 apply_rollback 失败但未报错"
        assert self.migration.failed_reason == '', "异常信息未被捕获"
        assert self.migration.finished, "执行 apply_rollback 后, migration 未标记为完成"


class TestBaseObjectMigration(BaseTestCaseForMigration):
    MIGRATION_CLS = BaseObjectMigration

    def test_migrate(self):
        assert self.context.app is None, "未运行 migrate 前, context 已绑定 app"
        self.migration.migrate()
        assert self.context.app, "migrate运行后, context 未绑定 app"
        code = self.context.legacy_app.code
        name = self.context.legacy_app.name
        # Application的code 和 name 全局唯一
        assert f"{name}[{code}]" == str(self.context.app), "context 绑定的app 与 legacy_app不一致"

    def test_rollback(self):
        self.migration.migrate()
        assert self.context.app, "context 未绑定 app"
        assert self.context.app.is_deleted is False, "app 已被删除"
        self.migration.rollback()
        assert self.context.app is None, "app 删除失败"


class TestMainInfoMigration(BaseTestCaseForMigration):
    MIGRATION_CLS = MainInfoMigration
    PRECONDITION_MIGRATION_CLS = [BaseObjectMigration]

    def test_migrate(self):
        # mock `create_engine_apps`
        assert self.context.app, "context 未绑定 app"
        app = self.context.app
        with pytest.raises(ObjectDoesNotExist):
            app.get_default_module()
        assert app.envs.count() == 0, "app 未绑定 ApplicationEnvironment"
        assert len(fetch_application_members(app.code)) == 0, "App 已绑定用户组"

        with global_mock(self.context):
            self.migration.migrate()

        assert app.envs.count() == len(
            ModuleInitializer.default_environments
        ), f"app 默认提供的运行环境数量不为 {len(ModuleInitializer.default_environments)}"
        assert app.modules.count() == 1, "迁移应用的模块数量不为 1"
        # TODO: 逐个判断 ADMINISTRATOR, DEVELOPER, OPERATOR 的人员
        assert len(fetch_application_members(app.code)) != 0, "绑定迁移应用的人员名单失败"

    def test_rollback(self):
        self.test_migrate()
        assert self.context.app, "context 未绑定 app"
        app = self.context.app
        self.migration.rollback()
        assert app.envs.count() == 0, "app 清理 ApplicationEnvironment 失败"
        assert len(fetch_application_members(app.code)) == 0, "App 清理用户组成员失败"
        assert app.modules.count() == 0, "app 清理 Modules 失败"


class TestSourceControlMigration(BaseTestCaseForMigration):
    MIGRATION_CLS = SourceControlMigration
    PRECONDITION_MIGRATION_CLS = [BaseObjectMigration, MainInfoMigration]

    def test_migrate(self):
        assert self.context.app, "context 未绑定 app"
        app = self.context.app
        module = app.get_default_module()
        assert not module.source_type, "模块已绑定源码类型"
        assert not module.source_repo_id, "模块已绑定源码仓库"
        self.migration.migrate()
        module = app.get_default_module()

    def test_rollback(self):
        self.test_migrate()
        assert self.context.app, "context 未绑定 app"
        self.migration.rollback()
        assert (
            SvnRepository.objects.filter(pk=self.context.app.default_module.source_repo_id).count() == 0
        ), "模块绑定的源码仓库对象未移除"


class TestProductMigration(BaseTestCaseForMigration):
    MIGRATION_CLS = ProductMigration
    PRECONDITION_MIGRATION_CLS = [BaseObjectMigration, MainInfoMigration, SourceControlMigration]

    def test_migrate(self):
        self.migration.migrate()
        product = Product.objects.get(application=self.context.app)
        # 不确定是否本地时区出错
        assert product.introduction == self.context.legacy_app.introduction, "同步 prudcut 的介绍信息错误"
        # 没有设置 桌面 db，则无法同步 tag信息
        if not getattr(settings, "BK_CONSOLE_DBCONF", None):
            assert product.tag is None
        else:
            assert product.tag.tagmap.remote_id == self.context.legacy_app.tags_id, "绑定 桌面tag 失败"
        display_options = DisplayOptions.objects.get(product=product)
        assert display_options.contact is None, "# 写该单元测试时, 未同步contact"

    @pytest.mark.usefixtures('init_tmpls')
    def test_migrate_when_released_to_market(self):
        """模拟应用迁移前已发布至市场, 市场功能需在同步 Product 才能正常访问"""
        self.context.legacy_app.is_display = 1
        self.context.legacy_app.is_already_online = 1
        self.context.session.commit()

        self.test_migrate()
        # 绑定 migration_process 与 Application
        self.context.migration_process.app = self.context.app
        self.context.migration_process.save()

        market_config, _ = MarketConfig.objects.get_or_create_by_app(self.context.app)
        assert market_config.enabled is False, "迁移时, 市场默认关闭"
        # 重新获取 legacy app, 避免数据缓存
        legacy_app = get_legacy_app(self.context.session, self.context.legacy_app.code)
        assert legacy_app.is_display == 1, "迁移时, 应用被错误下架"
        assert legacy_app.is_already_online == 1, "迁移时, 应用被错误下架"

    @pytest.mark.usefixtures('init_tmpls')
    def test_migrate_before_release_to_market(self):
        """模拟应用迁移前已发布至市场, 市场功能需在同步 Product 才能正常访问"""
        self.context.legacy_app.is_display = 0
        self.context.legacy_app.is_already_online = 0
        self.context.session.commit()

        self.test_migrate()
        market_config, _ = MarketConfig.objects.get_or_create_by_app(self.context.app)
        assert market_config.enabled is False, "迁移时, 市场默认关闭"
        # 重新获取 legacy app, 避免数据缓存
        legacy_app = get_legacy_app(self.context.session, self.context.legacy_app.code)
        assert legacy_app.is_display == 0, "迁移时, 应用被错误上架"
        assert legacy_app.is_already_online == 0, "迁移时, 应用被错误上架"

    def test_rollback(self):
        self.test_migrate()
        self.migration.rollback()
        assert DisplayOptions.objects.filter(product__code=self.context.app.code).count() == 0, "DisplayOptions 删除异常"
        assert Product.objects.filter(code=self.context.app.code).count() == 0, "Product 删除异常"
