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
import re
from typing import Optional

from django.db.models.signals import post_save
from django.dispatch import receiver
from sqlalchemy.exc import IntegrityError as SqlIntegrityError
from sqlalchemy.orm import Session

from paasng.accessories.publish.market.constant import AppState
from paasng.accessories.publish.market.models import MarketConfig, Product
from paasng.accessories.publish.market.signals import product_create_or_update_by_operator
from paasng.accessories.publish.sync_market.engine import RemoteAppManager
from paasng.accessories.publish.sync_market.managers import (
    AppDeveloperManger,
    AppManger,
    AppOpsManger,
    AppReleaseRecordManger,
)
from paasng.accessories.publish.sync_market.utils import run_required_db_console_config
from paasng.core.core.storages.sqlalchemy import console_db
from paasng.core.region.models import get_region
from paasng.infras.oauth2.models import OAuth2Client
from paasng.platform.applications.exceptions import AppFieldValidationError, IntegrityError
from paasng.platform.applications.models import Application, ApplicationEnvironment
from paasng.platform.applications.signals import (
    application_logo_updated,
    application_member_updated,
    before_finishing_application_creation,
    module_environment_offline_success,
    prepare_change_application_name,
    prepare_use_application_code,
    prepare_use_application_name,
)
from paasng.platform.engine.models import Deployment
from paasng.platform.engine.signals import post_appenv_deploy

try:
    from paasng.accessories.publish.sync_market.constant_ext import I18N_FIELDS_IN_CONSOLE
except ImportError:
    from paasng.accessories.publish.sync_market.constant import I18N_FIELDS_IN_CONSOLE

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Deployment)
@run_required_db_console_config
def deploy_handler(sender, instance, created, raw, using, update_fields, *args, **kwargs):
    """关注部署状态"""
    application = instance.app_environment.application
    is_default_module_prod_deploy_success = all(
        [
            instance.app_environment.environment == "prod",
            instance.app_environment.module == application.get_default_module(),
            instance.has_succeeded(),
        ]
    )
    if not is_default_module_prod_deploy_success:
        return

    product = application.get_product()
    if product is None:
        logger.warning("正式环境发布成功, 但 Product 对象不存在！")
        product = Product.objects.create_default_product(application=application)

    try:
        market_config, _ = MarketConfig.objects.get_or_create_by_app(application)
        market_config.on_release()
        on_product_deploy_success(product, "prod")
    except Exception:
        logger.exception("打开桌面入口失败！")


def on_product_deploy_success(product, environment, auto_enable_market=False, **kwargs):
    """
    app提测上线
    以后处于性能的考虑，可能只更新部分字段
    """
    application = product.application
    # 记录部署前的 product 状态
    product_state = product.state

    if product_state != AppState.RELEASED.value:
        logger.debug("product:%s state changed to %s", product.id, AppState.RELEASED.value)
        product.state = AppState.RELEASED.value
        product.save(update_fields=["state"])

    # no sync with not finished migration app
    if application.migrationprocess_set.exists() and application.migrationprocess_set.latest("id").is_active():
        return

    with console_db.session_scope() as session:
        manager = RemoteAppManager(product, session)
        sync_fields = [
            "state",  # 只有这个字段是上线状态，其它字段为更新应用属性
            "is_already_online",
            "created_date",
            "creater",
            "description",
            "introduction",
            "isresize",
            "issetbar",
            "language",
            "logo",
            "name",
            "tags_id",
            "width",
            "height",
            "open_mode",
        ]
        sync_fields.extend(I18N_FIELDS_IN_CONSOLE)
        manager.sync_data(sync_fields)

        # 同步开发者和运维人员名单
        sync_console_app_developers(application, session)
        sync_console_app_devopses(application, session)


@receiver(product_create_or_update_by_operator)
@run_required_db_console_config
def on_product_create_or_updated(product: Product, **kwargs):
    """
    app基本属性更新
    以后处于性能的考虑，可能只更新部分字段
    """
    application = product.application
    with console_db.session_scope() as session:
        try:
            manager = RemoteAppManager(product, session)
            sync_fields = [
                "created_date",
                "creater",
                "description",
                "introduction",
                "isresize",
                "issetbar",
                "language",
                "logo",
                "name",
                "tags_id",
                "width",
                "height",
                "open_mode",
                "visiable_labels",
            ]
            sync_fields.extend(I18N_FIELDS_IN_CONSOLE)
            manager.sync_data(sync_fields)
        except Exception:
            logger.exception("同步修改Product属性到桌面失败！")

        # 同步开发者和运维人员名单
        sync_console_app_developers(application, session)
        sync_console_app_devopses(application, session)


@receiver(application_member_updated)
@run_required_db_console_config
def update_console_members(sender, application, **kwargs):
    """
    主要功能: 当应用成员发生变更时, 同步信息至桌面
    """
    with console_db.session_scope() as session:
        sync_console_app_developers(application, session)
        sync_console_app_devopses(application, session)


def sync_console_app_developers(application: Application, session: Session):
    # sync developers(开发者) to console
    try:
        developers = application.get_developers()
        AppDeveloperManger(session).update_developers(application.code, developers)
    except Exception:
        logger.exception("同步开发者信息到桌面失败！")


def sync_console_app_devopses(application: Application, session: Session):
    # sync devops(运营人员) to console
    try:
        devopses = application.get_devopses()
        AppOpsManger(session).update_ops(application.code, devopses)
    except NotImplementedError:
        logger.info("op role is not defined, skip synchronization")
    except Exception:
        logger.exception("同步运营人员信息到桌面失败！")


@receiver(prepare_use_application_code)
@run_required_db_console_config
def validate_app_code_uniquely(sender, value: str, **kwargs):
    """Check if code already exists in legacy database, if exists, raise AppFieldValidationError"""
    with console_db.session_scope() as session:
        app = AppManger(session).get(code=value)
    if app:
        raise AppFieldValidationError("duplicated", "Application code=%s already exists" % value)


@receiver(prepare_use_application_name)
@run_required_db_console_config
def validate_app_name_uniquely(sender, value: str, instance: Optional["Application"] = None, **kwargs):
    """Check if name already exists in legacy database, if exists, raise AppFieldValidationError

    :param instance: if given, will not raise error when the existed object belongs to given instance
    """
    code = instance.code if instance else None

    with console_db.session_scope() as session:
        is_unique = AppManger(session).verify_name_is_unique(value, code)
    if not is_unique:
        raise AppFieldValidationError("duplicated", "Application name=%s already exists" % value)


@receiver(before_finishing_application_creation)
@run_required_db_console_config
def register_app_core_data(sender, application: Application, **kwargs):
    """
    主要功能：实现paas2.0与paas3.0中app的code和name唯一
    实现原理：第一次创建应用时，首先尝试到老版本paas表中添加一条记录，占用code和name，
            这样paas2.0就无法创建跟3.0 code或name相同的app

    :raises: IntegrityError when application with the same code already exists in legacy database
    """
    try:
        register_application_with_default(application.region, application.code, application.name)
    except SqlIntegrityError as e:
        if len(e.args) > 0:
            error_msg = e.args[0]
            if re.search("Duplicate entry '.*' for key '.*code'", error_msg):
                raise IntegrityError(field="code")
            elif re.search("Duplicate entry '.*' for key '.*name'", error_msg):
                raise IntegrityError(field="name")
            else:
                raise
        else:
            raise


@receiver(prepare_change_application_name)
@run_required_db_console_config
def on_change_application_name(sender, code: str, name: Optional[str] = None, name_en: Optional[str] = None, **kwargs):
    """直接修改，占用名称"""
    with console_db.session_scope() as session:
        app = AppManger(session).get(code)
        if not app:
            raise AppFieldValidationError("not_exist", "Application code=%s does not exist" % code)

        update_fields = {}
        if name:
            update_fields["name"] = name
        if name_en:
            update_fields["name_en"] = name_en

        try:
            AppManger(session).update(code, update_fields)
        except SqlIntegrityError:
            raise IntegrityError(field="name")


def register_application_with_default(region, code, name):
    """使用默认数据注册到蓝鲸桌面DB（占用code和name字段）"""
    deploy_ver = get_region(region).basic_info.legacy_deploy_version
    with console_db.session_scope() as session:
        app = AppManger(session).create(code, name, deploy_ver, from_paasv3=True)
        # 应用注册完毕, 开始同步开发者信息
        try:
            application = Application.objects.get(code=code)
            sync_console_app_developers(application, session)
            sync_console_app_devopses(application, session)
        except Exception:
            logger.exception("同步应用开发者信息至桌面失败!")
    return app


@receiver(post_save, sender=OAuth2Client)
@run_required_db_console_config
def application_oauth_handler(sender, instance, created, raw, using, update_fields, *args, **kwargs):
    """监听App权限信息初始化, 同步写secrete key到console db"""
    with console_db.session_scope() as session:
        if instance.client_secret:
            AppManger(session).sync_oauth(
                region=instance.region, code=instance.client_id, secret=instance.client_secret
            )


@receiver(module_environment_offline_success)
@run_required_db_console_config
def offline_handler(sender, offline_instance, environment, **kwargs):
    """模块环境下架回调, 关于同步市场状态的逻辑"""
    application = offline_instance.app_environment.application
    module = offline_instance.app_environment.module

    # no sync with not finished migration app
    if application.migrationprocess_set.exists() and application.migrationprocess_set.last().is_active():
        return

    # 当且仅当下架`主模块`的`正式环境`时, 才会同步市场逻辑
    if not (module.is_default and offline_instance.app_environment.is_production()):
        return

    product = application.get_product()
    if product and product.state != AppState.OFFLINE.value:
        product.state = AppState.OFFLINE.value
        product.save(update_fields=["state"])

        update_data = {
            # 0 表示已下架
            "state": 0,
            "is_already_online": 0,
        }
        with console_db.session_scope() as session:
            AppManger(session).update(application.code, update_data)

    market_config, _ = MarketConfig.objects.get_or_create_by_app(application)
    market_config.on_offline()


@receiver(post_save, sender=MarketConfig)
@run_required_db_console_config
def market_config_update_handler(sender, instance: MarketConfig, created: bool, **kwargs):
    """同步V3的市场配置到蓝鲸应用市场"""
    # 新建的 MarketConfig 不往市场同步(因为默认值都是关闭的, 避免影响现有配置)
    if created:
        return

    application = instance.application
    if application.migrationprocess_set.exists() and application.migrationprocess_set.last().is_active():
        # 对于正在迁移至v3的应用，不同步市场配置
        return

    product = application.get_product()
    if product is None:
        logger.warning("未创建 product, 不同步信息至市场")
        return

    with console_db.session_scope() as session:
        sync_fileds = [
            # state 字段描述应用的开发状态，影响能不能在市场上被搜索
            "state",
            # is_already_online 字段描述应用是否已发布至正式环境, 影响打开应用后是否提示已下架
            "is_already_online",
            # 修复历史的脏数据, is_display 总是为 True
            "is_display",
            # 精简版应用、独立域名应用、独立子域名应用均需要同步 external_url
            "external_url",
            # is_mapp 字段描述 app 是否移动端应用
            "is_mapp",
            # use_mobile_online 字段描述 app 是否在移动端(正式)使用
            "use_mobile_online",
            # use_mobile_test 字段描述 app 是否在移动端(测试)使用
            "use_mobile_test",
            # 移动端访问地址
            "mobile_url_test",
            "mobile_url_prod",
        ]
        if not instance.application.engine_enabled:
            # 精简版应用特殊处理
            # 首次发布市场时, 更新 首次提测时间 和 首次上线时间; P.S. state = 1 表示`开发中`, 是 state 的初始值
            app = AppManger(session).get(application.code)
            if app and app.state == 1:
                sync_fileds.extend(["first_test_time", "first_online_time"])

        try:
            # 复用 RemoteAppManager, 集中管理同步逻辑
            manager = RemoteAppManager(product, session)
            manager.sync_data(sync_fileds)
        except Exception:
            logger.exception("同步修改Product属性到桌面失败！")


@run_required_db_console_config
def sync_external_url_to_market(application: Application):
    """同步访问地址至应用市场"""
    market_config = application.market_config
    if not market_config.enabled:
        # 市场未开启, 不进行同步
        return

    product = application.get_product()
    if product is None:
        logger.warning("未创建 product, 不同步信息至市场")
        return

    with console_db.session_scope() as session:
        try:
            # 复用 RemoteAppManager, 集中管理同步逻辑
            manager = RemoteAppManager(product, session)
            # 精简版应用、独立域名应用、独立子域名应用均需要同步 external_url
            manager.sync_data(["external_url"])
        except Exception:
            logger.exception("同步修改Product属性到桌面失败！")


@receiver(post_appenv_deploy)
@run_required_db_console_config
def sync_release_record(sender: ApplicationEnvironment, deployment: Deployment, **kwargs):
    """Sync a release record to legacy database when a deployment has been finished successfully"""
    if not deployment.has_succeeded():
        return

    application = sender.application
    # Only sync prod deployment
    if not (deployment.has_succeeded() and sender.environment == "prod"):
        return

    try:
        with console_db.session_scope() as session:
            AppReleaseRecordManger(session).create(application.code, deployment.operator, sender.environment)
    except Exception:
        logger.exception(f"Unable to sync deployment for {application.code}")


try:
    # Load external handlers
    from . import handlers_ext  # type: ignore  # noqa: F401
except ImportError:
    pass


@receiver(application_logo_updated)
def sync_logo(sender, application: Application, **kwargs):
    """Sync application's logo when updated"""
    if not application.has_customized_logo():
        return

    # Skip syncing if product was not created yet
    try:
        product = Product.objects.get(application=application)
    except Product.DoesNotExist:
        return

    with console_db.session_scope() as session:
        try:
            RemoteAppManager(product, session).sync_data(["logo"])
        except Exception:
            logger.exception("Unable to sync application logo to market")
