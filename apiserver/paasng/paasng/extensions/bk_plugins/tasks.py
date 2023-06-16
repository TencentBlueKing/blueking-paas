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

from celery import shared_task
from django.utils.translation import gettext_lazy as _

from paasng.engine.constants import AppEnvName
from paasng.engine.deploy.archive import OfflineManager
from paasng.engine.exceptions import OfflineOperationExistError
from paasng.engine.models import Deployment
from paasng.platform.applications.models import Application

logger = logging.getLogger(__name__)


@shared_task
def archive_prod_env(app_code: str, operator: str):
    """下架插件应用默认模块的Prod环境

    :param str app_code: 需要下架的应用ID
    :param str operator: 编码后的操作人用户名
    """
    application = Application.objects.get(code=app_code)
    module = application.get_default_module()
    prod = module.get_envs(environment=AppEnvName.PROD)

    manager = OfflineManager(prod)
    log_extra = {"app_code": app_code, "action": "plugin.archive"}

    try:
        manager.perform_env_offline(operator=operator)
    except Deployment.DoesNotExist:
        # 未曾部署，跳过该环境的下架操作
        logger.warning("该插件<%s>未曾部署，跳过该环境的下架操作", str(application))
    except OfflineOperationExistError:
        logger.exception(_("存在正在进行的下架任务，请勿重复操作"), extra=log_extra)
    except Exception:
        logger.exception("app offline error", extra=log_extra)
