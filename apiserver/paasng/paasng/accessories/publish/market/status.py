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

from paasng.accessories.publish.market.models import MarketConfig, Product
from paasng.accessories.publish.sync_market.handlers import on_product_deploy_success
from paasng.accessories.publish.sync_market.utils import run_required_db_console_config
from paasng.platform.engine.models import Deployment

logger = logging.getLogger(__name__)


@run_required_db_console_config
def publish_to_market_by_deployment(deployment: Deployment):
    """Publish the application to market, triggered by a finished deployment.

    :param deployment: The finished deployment object.
    """
    if not _is_default_prod_success(deployment):
        return

    application = deployment.app_environment.application
    product = application.get_product()
    if product is None:
        logger.warning("The product object missing for app: %s", application.code)
        product = Product.objects.create_default_product(application=application)

    try:
        market_config, _ = MarketConfig.objects.get_or_create_by_app(application)
        market_config.on_release()
        on_product_deploy_success(product, "prod")
    except Exception:
        logger.exception("Unable to publish to market for app: %s", application.code)


def _is_default_prod_success(deployment: Deployment) -> bool:
    """Check if the deployment is on the default module's prod environment and has succeeded."""
    return all(
        (
            deployment.app_environment.environment == "prod",
            deployment.app_environment.module.is_default,
            deployment.has_succeeded(),
        )
    )
