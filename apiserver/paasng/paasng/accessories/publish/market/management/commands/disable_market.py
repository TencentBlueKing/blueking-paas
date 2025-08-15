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

from django.core.management.base import BaseCommand

from paasng.accessories.publish.market.models import MarketConfig
from paasng.accessories.publish.sync_market.handlers import market_config_update_handler
from paasng.platform.applications.models import Application


class Command(BaseCommand):
    """
    支持关闭市场
    """

    def add_arguments(self, parser):
        parser.add_argument("--app-code", dest="app_code", required=True, help="应用code")

    def handle(self, app_code: str, *args, **kwargs):
        try:
            app = Application.objects.get(code=app_code)
        except Application.DoesNotExist:
            self.stdout.write(f"应用({app_code})不存在!")
            return

        market_config = MarketConfig.objects.update_enabled(app, False)
        market_config_update_handler(sender=market_config, instance=market_config, created=False)
        self.stdout.write(f"已关闭应用({app_code})的市场配置.")
