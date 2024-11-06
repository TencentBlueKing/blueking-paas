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

from django.dispatch import receiver

from paasng.misc.monitoring.monitor.dashboards.tasks import import_builtin_dashboards
from paasng.platform.applications.models import ApplicationEnvironment
from paasng.platform.engine.models.deployment import Deployment
from paasng.platform.engine.signals import post_appenv_deploy

logger = logging.getLogger(__name__)


@receiver(post_appenv_deploy)
def import_dashboard_after_deploy(sender: ApplicationEnvironment, deployment: Deployment, **kwargs):
    if not deployment.has_succeeded():
        return

    import_builtin_dashboards.delay(sender.application.code)
