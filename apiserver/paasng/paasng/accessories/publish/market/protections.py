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

"""Preconditions for publish Application/Module"""

from django.utils.translation import gettext as _

from paasng.accessories.publish.entrance.exposer import env_is_deployed
from paasng.accessories.publish.market.constant import ProductSourceUrlType
from paasng.accessories.publish.market.models import MarketConfig, Product
from paasng.core.core.protections.base import BaseCondition, BaseConditionChecker
from paasng.core.core.protections.exceptions import ConditionNotMatched
from paasng.platform.applications.models import Application
from paasng.platform.modules.models import Module


class PublishCondition(BaseCondition):
    """Abstract base class for publish condition"""

    def __init__(self, application: Application):
        self.application = application

    def validate(self):
        raise NotImplementedError


class ProductInfoCondition(PublishCondition):
    """检查是否已经完善应用信息"""

    action_name = "fill_product_info"

    def validate(self):
        if not Product.objects.filter(application=self.application).exists():
            raise ConditionNotMatched(_("未完善应用市场信息"), self.action_name)


class ProdEnvReadinessCondition(PublishCondition):
    """检查生产环境是否准备就绪"""

    action_name = "deploy_prod_env"

    def validate(self):
        market_config, _created = MarketConfig.objects.get_or_create_by_app(self.application)
        if market_config.source_url_type in [
            ProductSourceUrlType.DISABLED,
            ProductSourceUrlType.THIRD_PARTY,
        ]:
            return

        app_env = market_config.source_module.envs.get(environment="prod")
        if not env_is_deployed(app_env):
            raise ConditionNotMatched(_("应用未在生产环境成功部署"), self.action_name)


class SourceURLValidationConditon(PublishCondition):
    """检查无引擎应用是否设置有效的访问地址"""

    action_name = "fill_thirdparty_url"

    def validate(self):
        if self.application.engine_enabled:
            return
        market_config, _created = MarketConfig.objects.get_or_create_by_app(self.application)
        if market_config.source_url_type == ProductSourceUrlType.THIRD_PARTY.value and not market_config.source_tp_url:
            raise ConditionNotMatched(_("未设置合法的第三方地址"), self.action_name)
        if market_config.source_url_type == ProductSourceUrlType.DISABLED.value:
            raise ConditionNotMatched(_("未设置有效的访问地址"), self.action_name)


class AppPublishPreparer(BaseConditionChecker):
    """Prepare for publishing application to market"""

    condition_classes = [ProductInfoCondition, ProdEnvReadinessCondition, SourceURLValidationConditon]

    def __init__(self, application: Application):
        self.application = application
        self.conditions = [cls(application) for cls in self.condition_classes]

    def __str__(self):
        return f"Application<{self.application.code}>"


class ModulePublishCondition(BaseCondition):
    """Abstract base class for publish condition"""

    def __init__(self, module: Module):
        self.module = module


class ModuleProdEnvReadinessCondition(ModulePublishCondition):
    """检查模块正式环境是否就绪"""

    action_name = "deploy_prod_env"

    def validate(self):
        app_env = self.module.get_envs("prod")
        if not env_is_deployed(app_env):
            raise ConditionNotMatched(_("模块未在生产环境成功部署"), self.action_name)


class ModulePublishPreparer(BaseConditionChecker):
    """Prepare to publish a module"""

    # 目前只在市场开启的情况下检查
    condition_classes = [ModuleProdEnvReadinessCondition]

    def __init__(self, module: Module):
        self.module = module
        self.conditions = [cls(module) for cls in self.condition_classes]

    def __str__(self):
        return f"Module<{self.module.name}>"
