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

from django.core.management.base import BaseCommand

from paas_wl.bk_app.dev_sandbox.controller import DevSandboxWithCodeEditorController
from paasng.accessories.dev_sandbox.models import DevSandbox


class Command(BaseCommand):
    help = "=回收沙箱"

    def add_arguments(self, parser):
        parser.add_argument(
            "--app_code",
            required=False,
            dest="app_code",
            type=str,
            help="application code of the dev sandbox",
        )

        parser.add_argument(
            "--module_name",
            required=False,
            dest="module_name",
            type=str,
            help="module name of the dev sandbox",
        )

        parser.add_argument(
            "--user_id",
            required=False,
            dest="user_id",
            help="owner id of the dev sandbox",
        )

        parser.add_argument(
            "--only_expired",
            dest="only_expired",
            action="store_false",
            default=True,
            help="only recycle expired dev sandboxes",
        )

    def handle(self, app_code, module_name, user_id, only_expired, *args, **options):
        qs = DevSandbox.objects.all()
        if app_code:
            qs = qs.filter(module__application__code=app_code)
            if module_name:
                qs = qs.filter(module__name=module_name)

        if user_id:
            qs = qs.filter(owner=user_id)

        for dev_sandbox in qs:
            controller = DevSandboxWithCodeEditorController(
                app=dev_sandbox.module.application,
                module_name=dev_sandbox.module.name,
                dev_sandbox_code=dev_sandbox.code,
                owner=dev_sandbox.owner,
            )
            if not only_expired or dev_sandbox.is_expired():
                controller.delete()
                dev_sandbox.delete()
