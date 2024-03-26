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

from paasng.misc.monitoring.monitor.alert_rules.manager import alert_rule_manager_cls
from paasng.platform.applications.models import Application

logger = logging.getLogger(__name__)


@shared_task
def create_rules(app_code: str, module_name: str, run_env: str):
    try:
        rule_mgr = alert_rule_manager_cls(Application.objects.get(code=app_code))
        rule_mgr.create_rules(module_name, run_env)
    except Exception:
        logger.exception(
            f"Unable to create alert rules after release app"
            f"(code: {app_code}, module: {module_name}, run_env: {run_env})"
        )


@shared_task
def update_notice_group(app_code: str):
    try:
        rule_mgr = alert_rule_manager_cls(Application.objects.get(code=app_code))
        rule_mgr.update_notice_group()
    except Exception:
        logger.exception(f"Unable to update notice group (code: {app_code})")
