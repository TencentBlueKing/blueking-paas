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

from celery import shared_task

from paasng.misc.monitoring.monitor.dashboards.manager import bk_dashboard_manager_cls
from paasng.platform.applications.models import Application

logger = logging.getLogger(__name__)


@shared_task
def import_builtin_dashboards(app_code: str):
    """导入内置仪表盘，普通应用和插件应用分别导入各自的仪表盘

    Note: 这里只做初始化导入，仪表盘版本升级在单独的脚本里面按需执行
    """
    try:
        dashboard_manager = bk_dashboard_manager_cls(Application.objects.get(code=app_code))
        dashboard_manager.init_builtin_dashboard()
    except Exception:
        logger.exception(f"Unable to import builtin dashboards after release app(code: {app_code})")
