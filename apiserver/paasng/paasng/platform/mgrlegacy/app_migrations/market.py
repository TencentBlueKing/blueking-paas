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

from django.utils.translation import gettext_lazy as _

from paasng.accessories.publish.market.constant import ProductSourceUrlType
from paasng.accessories.publish.market.models import MarketConfig
from paasng.platform.mgrlegacy.app_migrations.base import BaseMigration

logger = logging.getLogger(__name__)


class MarketMigration(BaseMigration):
    def get_description(self):
        return _("同步应用市场信息")

    def migrate(self):
        app = self.context.app

        # 应用市场信息
        MarketConfig.objects.update_or_create(
            application=app,
            defaults=dict(
                region=app.region,
                # PaaS2.0 中部署到了正式环境则表示启用应用市场服务
                enabled=self.context.legacy_app_proxy.is_prod_deployed(),
                # 当 auto_enable_when_deploy 为 True 时, 部署后即自动上架到市场; 否则就不会
                auto_enable_when_deploy=True,
                source_module=app.get_default_module(),
                source_url_type=ProductSourceUrlType.THIRD_PARTY.value,
                source_tp_url=self.context.legacy_app.external_url,
            ),
        )

    def rollback(self):
        MarketConfig.objects.filter(application__code=self.context.app.code).delete()
