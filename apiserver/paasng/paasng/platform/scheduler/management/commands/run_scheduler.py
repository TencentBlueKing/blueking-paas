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
import signal

from django.core.management.base import BaseCommand

from paasng.platform.scheduler.jobs import scheduler

logger = logging.getLogger(__name__)


def shutdown_gracefully(sig, frame):
    logger.info("shutdowning scheduler")
    scheduler.shutdown()


class Command(BaseCommand):
    help = "Run apscheduler"

    def handle(self, *args, **options):
        signal.signal(signal.SIGINT, shutdown_gracefully)
        signal.signal(signal.SIGTERM, shutdown_gracefully)

        scheduler.start()
