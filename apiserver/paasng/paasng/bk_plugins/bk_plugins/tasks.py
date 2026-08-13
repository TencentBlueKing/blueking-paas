# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

from celery import shared_task
from django.utils.translation import gettext_lazy as _

from paasng.platform.applications.models import Application
from paasng.platform.engine.constants import AppEnvName
from paasng.platform.engine.deploy.archive import start_archive_step
from paasng.platform.engine.exceptions import OfflineOperationExistError
from paasng.platform.engine.models import Deployment

from .apigw import safe_sync_apigw_maintainers
from .models import is_bk_plugin

logger = logging.getLogger(__name__)


@shared_task
def sync_plugin_apigw_maintainers(app_code: str):
    """插件应用成员变更后，全量刷新其 API 网关的维护者名单

    :param str app_code: 发生成员变更的应用 ID
    """
    application = Application.objects.get(code=app_code)
    # 仅对插件应用执行网关维护者同步
    if not is_bk_plugin(application):
        logger.debug('Syncing apigw maintainers: "%s" is not plugin type, will not proceed.', app_code)
        return

    safe_sync_apigw_maintainers(application)


@shared_task
def archive_prod_env(app_code: str, operator: str):
    """下架插件应用默认模块的Prod环境

    :param str app_code: 需要下架的应用ID
    :param str operator: 编码后的操作人用户名
    """
    application = Application.objects.get(code=app_code)
    module = application.get_default_module()
    prod = module.get_envs(environment=AppEnvName.PROD)

    log_extra = {"app_code": app_code, "action": "plugin.archive"}

    try:
        start_archive_step(prod, operator=operator)
    except Deployment.DoesNotExist:
        # 未曾部署，跳过该环境的下架操作
        logger.warning("该插件<%s>未曾部署，跳过该环境的下架操作", str(application))
    except OfflineOperationExistError:
        logger.exception(_("存在正在进行的下架任务，请勿重复操作"), extra=log_extra)
    except Exception:
        logger.exception("app offline error", extra=log_extra)
