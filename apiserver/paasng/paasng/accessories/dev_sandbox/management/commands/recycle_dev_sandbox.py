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
    python manage.py recycle_dev_sandbox --only_expired false
"""

from django.core.management.base import BaseCommand

from paas_wl.bk_app.dev_sandbox.controller import DevSandboxWithCodeEditorController
from paasng.accessories.dev_sandbox.models import DevSandbox


class Command(BaseCommand):
    help = "回收沙箱"

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            dest="all",
            action="store_true",
            help="recycle all dev sandboxes",
        )

    def handle(self, all, *args, **options):
        for dev_sandbox in DevSandbox.objects.all():
            controller = DevSandboxWithCodeEditorController(
                app=dev_sandbox.module.application,
                module_name=dev_sandbox.module.name,
                dev_sandbox_code=dev_sandbox.code,
                owner=dev_sandbox.owner,
            )
            if all or dev_sandbox.is_expired():
                controller.delete()
                dev_sandbox.delete()
