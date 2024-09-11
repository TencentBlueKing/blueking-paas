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

from django.dispatch import receiver

from paasng.accessories.publish.market.models import MarketConfig
from paasng.platform.applications.signals import application_default_module_switch


@receiver(application_default_module_switch)
def update_market_config_source_module(sender, application, new_module, old_module, **kwargs):
    """更新应用主模块时需要同步更新应用市场配置中模块信息，否则会导致发布条件判断出现问题"""
    try:
        market_config = application.market_config
        market_config.source_module = new_module
        market_config.save()
    except MarketConfig.DoesNotExist:
        pass
