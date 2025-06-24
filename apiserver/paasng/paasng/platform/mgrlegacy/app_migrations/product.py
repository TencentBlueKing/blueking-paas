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

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from paasng.accessories.publish.market.models import ApplicationExtraInfo, DisplayOptions, Product, Tag
from paasng.accessories.publish.market.signals import product_create_or_update_by_operator
from paasng.accessories.publish.sync_market.models import TagMap
from paasng.platform.mgrlegacy.app_migrations.base import BaseMigration

logger = logging.getLogger(__name__)


class ProductMigration(BaseMigration):
    """Create Product without sync to bk_console"""

    def get_description(self):
        return _("同步产品信息")

    def migrate(self):
        app = self.context.app
        # BK_CONSOLE_DBCONF has a default value of None
        if getattr(settings, "BK_CONSOLE_DBCONF", None):
            tag = TagMap.objects.get(remote_id=self.legacy_app.tags_id).tag
        else:
            tag = Tag.objects.filter(parent__isnull=False).first()

        # migrate market app info
        kwargs = dict(
            application=app,
            code=app.code,
            name_en=app.name_en,
            name_zh_cn=app.name,
            introduction_en=self.legacy_app.introduction,
            introduction_zh_cn=self.legacy_app.introduction,
            description_en=self.context.legacy_app_proxy.get_app_description(),
            description_zh_cn=self.context.legacy_app_proxy.get_app_description(),
            type=self.context.legacy_app_proxy.get_app_type(),
            tenant_id=app.tenant_id,
        )
        product = Product.objects.create(**kwargs)
        product.created = self.legacy_app.created_date
        product.save(update_fields=["created"])

        ApplicationExtraInfo.objects.update_or_create(
            application=app,
            tenant_id=app.tenant_id,
            defaults={"tag": tag},
        )

        DisplayOptions.objects.create(
            product=product,
            visible=self.legacy_app.is_display,
            width=self.legacy_app.width or 890,
            height=self.legacy_app.height or 550,
            is_win_maximize=self.legacy_app.is_max,
            resizable=self.context.legacy_app_proxy.is_app_resizable(),
            tenant_id=app.tenant_id,
        )

        # 迁移logo到rgw
        logo = self.context.legacy_app_proxy.get_logo_file()
        if logo is not None:
            kwargs["logo"] = logo

        filename = self.context.legacy_app_proxy.get_logo_filename()
        app.logo.save(filename, logo, save=False)
        app.save()

        # After create `Product`, we would invoke some callback(such as create Operation Log) by sending this signal.
        product_create_or_update_by_operator.send(
            sender=self.__class__, product=product, operator=self.context.owner, created=True
        )

    def rollback(self):
        DisplayOptions.objects.filter(product__code=self.context.app.code).delete()
        Product.objects.filter(code=self.context.app.code).delete()
