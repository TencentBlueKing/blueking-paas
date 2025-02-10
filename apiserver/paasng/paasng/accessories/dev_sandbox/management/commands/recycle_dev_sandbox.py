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

"""Recycle dev sandbox.

By default, only expired sandboxes are recycled. Use the --all flag to recycle all sandboxes.

Examples:

    # 仅回收过期沙箱
    python manage.py recycle_dev_sandbox

    # 全量回收沙箱
    python manage.py recycle_dev_sandbox --all
"""

import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from paas_wl.bk_app.dev_sandbox.controller import DevSandboxController
from paasng.accessories.dev_sandbox.models import DevSandbox

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "回收沙箱"

    def add_arguments(self, parser):
        parser.add_argument("--all", dest="all", action="store_true", help="recycle all dev sandboxes")

    def handle(self, all, *args, **options):
        dev_sandboxes = DevSandbox.objects.all()
        if not all:
            dev_sandboxes = dev_sandboxes.filter(expired_at__lte=timezone.now())

        if not dev_sandboxes.exists():
            logger.info("No expired dev sandboxes to recycle")
            return

        logger.info("Recycling %d expired dev sandboxes", dev_sandboxes.count())
        for ds in dev_sandboxes:
            mod = ds.module
            logger.info("Recycle dev sandbox: %s (app: %s, module: %s)", ds.code, mod.application.code, mod.name)
            controller = DevSandboxController(module=ds.module, dev_sandbox_code=ds.code)
            controller.delete()
            ds.delete()
