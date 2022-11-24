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

from django.dispatch import receiver

from paasng.platform.applications.signals import application_default_module_switch

logger = logging.getLogger(__name__)


@receiver(application_default_module_switch)
def sync_market_for_module_switching(sender, application, new_module, old_module, **kwargs):
    """Update MarketConfig's source_module when application's default module has been changed"""
    logger.info(f"Changing application[{application.code}]'s source_module to {new_module.name}...")
    application.market_config.source_module = new_module
    application.market_config.save(update_fields=["source_module"])
