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
import base64
import logging
import os
from dataclasses import dataclass

import yaml
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import IntegrityError as DjangoIntegrityError
from django.db.models.signals import post_save
from django.db.transaction import atomic

from paasng.accessories.iam.exceptions import BKIAMGatewayServiceError
from paasng.accessories.iam.helpers import delete_builtin_user_groups, delete_grade_manager
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.exceptions import IntegrityError
from paasng.platform.applications.handlers import application_logo_updated
from paasng.platform.applications.helpers import register_builtin_user_groups_and_grade_manager
from paasng.platform.applications.models import Application
from paasng.platform.applications.signals import before_finishing_application_creation
from paasng.platform.applications.specs import AppSpecs
from paasng.platform.applications.utils import create_default_module
from paasng.platform.core.storages.sqlalchemy import console_db
from paasng.platform.oauth2.models import OAuth2Client
from paasng.platform.oauth2.utils import create_oauth2_client
from paasng.publish.market.constant import AppState, AppType, OpenMode, ProductSourceUrlType
from paasng.publish.market.models import DisplayOptions, MarketConfig, Product, Tag
from paasng.publish.market.signals import product_create_or_update_by_operator
from paasng.publish.sync_market.handlers import (
    application_oauth_handler,
    market_config_update_handler,
    sync_external_url_to_market,
)
from paasng.publish.sync_market.managers import AppManger
from paasng.utils.validators import str2bool

logger = logging.getLogger(__name__)


@dataclass
class Simple3rdAppDesc:
    code: str
    name: str
    name_en: str
    tag: str
    logo: str
    introduction_zh_cn: str
    introduction_en: str
    source_tp_url: str
    region: str = "default"
    creator: str = "admin"


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--source', type=str, dest="source")
        parser.add_argument('--app_codes', type=str, dest="third_app_init_codes")
        parser.add_argument('--override', type=str2bool, dest="override", default=False)
        parser.add_argument('--dry_run', dest="dry_run", action='store_true')

    def handle(self, source, third_app_init_codes, override, dry_run, *args, **options):
        """批量创建第三方应用"""
        with open(source, 'r') as f:
            apps = yaml.safe_load(f)

            for app in apps:
                desc = Simple3rdAppDesc(**app)
                if dry_run:
                    logger.info("DRY-RUN: going to create App according to desc: %s", desc)
                    continue

                third_app_init_codes = third_app_init_codes.strip()
                third_app_init_code_list = third_app_init_codes.split(",") if third_app_init_codes else []
                if desc.code not in third_app_init_code_list:
                    logger.info("app(code:%s) not exists in THIRD_APP_INIT_CODE_LIST, skip create", desc.code)
                    continue

                session = console_db.get_scoped_session()
                legacy_app = AppManger(session).get(desc.code)
                # 如果未设置强制替换参数 override，则应用 code 已经存在则不执行更新操作
                if (not override) and legacy_app:
                    logger.info("app(code:%s) exists in PaaS2.0, skip create", desc.code)
                    continue

                logger.info("going to create App according to desc: %s", f"{desc.name} - {desc.code}")
                with atomic():
                    self.create_3rd_app(desc)

    def get_app_secret_key(self, code: str) -> str:
        session = console_db.get_scoped_session()
        legacy_app = AppManger(session).get(code)
        if legacy_app:
            return legacy_app.auth_token
        return ''

    def create_oauth_client_by_code(self, code: str, region: str):
        secret_key = self.get_app_secret_key(code)
        # secret_key 已经存在，则使用已有的值
        if secret_key:
            # 由 bk-oauth 服务纳管应用信息后，则不需要再往 OAuth2Client 表中同步数据
            if not settings.ENABLE_BK_OAUTH:
                try:
                    # Disable signal to avoid data sync
                    post_save.disconnect(receiver=application_oauth_handler, sender=OAuth2Client)
                    OAuth2Client.objects.get_or_create(
                        region=region,
                        client_id=code,
                        defaults={'client_secret': secret_key},
                    )
                finally:
                    post_save.connect(receiver=application_oauth_handler, sender=OAuth2Client)
                    logger.info("create oauth app(code:%s) with an existing key", code)
        else:
            # secret_key 不存在，则生成一个新的
            create_oauth2_client(code, region)
            logger.info("create oauth app(code:%s) with a new randomly generated key", code)

    def create_3rd_app(self, app_desc: Simple3rdAppDesc):
        try:
            application, created = Application.objects.update_or_create(
                code=app_desc.code,
                region=app_desc.region,
                defaults={
                    'name': app_desc.name,
                    'name_en': app_desc.name_en,
                    'type': ApplicationType.ENGINELESS_APP,
                    'owner': app_desc.creator,
                    'creator': app_desc.creator,
                },
            )
        except DjangoIntegrityError:
            logger.info("app(name:%s) exists, skip create", app_desc.name)
            return

        if created:
            try:
                register_builtin_user_groups_and_grade_manager(application)
            except BKIAMGatewayServiceError as e:
                logger.exception("app initialize members failed, skip create: %s", e.message)
                return

            try:
                before_finishing_application_creation.send("FakeSender", application=application)
            except IntegrityError as e:
                logger.error(f"app with the same {e.field} field already exists in paas2.0, skip create")
                # 同步 PaaS2.0 失败，则同步删除 PaaS3.0 中已经创建的内容，权限中心先删除用户组，再删除分级管理员
                delete_builtin_user_groups(application.code)
                delete_grade_manager(application.code)
                Application.objects.filter(code=app_desc.code).delete()
                return

        if created:
            module = create_default_module(application)
            self.create_oauth_client_by_code(app_desc.code, app_desc.region)
        else:
            module = application.get_default_module()

        market_config, _ = MarketConfig.objects.update_or_create(
            region=application.region,
            application=application,
            defaults={
                'enabled': True,
                'auto_enable_when_deploy': not AppSpecs(application).confirm_required_when_publish,
                'source_module': module,
                'source_url_type': ProductSourceUrlType.THIRD_PARTY.value,
                'source_tp_url': os.path.expandvars(app_desc.source_tp_url),
            },
        )
        product, p_created = Product.objects.update_or_create(
            application=application,
            code=app_desc.code,
            defaults={
                'name_zh_cn': app_desc.name,
                'name_en': app_desc.name_en,
                'tag': Tag.objects.get(name=app_desc.tag),
                'introduction_zh_cn': app_desc.introduction_zh_cn,
                'introduction_en': app_desc.introduction_en,
                'type': AppType.THIRD_PARTY.value,
                'state': AppState.RELEASED.value,
            },
        )
        img_format, img_str = app_desc.logo.split(';base64,')
        ext = img_format.split('/')[-1]
        img_name = 'templogo.' + ext
        # # update product logo
        application.logo.save(name=img_name, content=ContentFile(base64.b64decode(img_str), name=img_name), save=False)
        application.save()
        # Send signal to trigger extra processes for logo
        application_logo_updated.send(sender=application, application=application)
        # 默认为从新标签页面打开
        DisplayOptions.objects.update_or_create(product=product, open_mode=OpenMode.NEW_TAB.value)

        # 同步应用基本信息、市场信息到桌面
        product_create_or_update_by_operator.send(
            sender=product, product=product, operator=app_desc.creator, created=p_created
        )
        # 同步应用访问地址到桌面
        sync_external_url_to_market(application=application)
        # 同步市场配置到蓝鲸应用市场
        market_config_update_handler(sender=market_config, instance=market_config, created=False)
