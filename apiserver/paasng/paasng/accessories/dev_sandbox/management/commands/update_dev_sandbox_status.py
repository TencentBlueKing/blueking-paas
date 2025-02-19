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

import requests
from django.core.management.base import BaseCommand
from rest_framework import status

from paas_wl.bk_app.dev_sandbox.controller import DevSandboxController
from paasng.accessories.dev_sandbox.models import DevSandbox


class Command(BaseCommand):
    help = "update status of all dev sandboxes"

    def handle(self, *args, **options):
        for dev_sandbox in DevSandbox.objects.all():
            try:
                detail = DevSandboxController(dev_sandbox).get_detail()
            except Exception as e:
                # 防止沙箱资源被管理员删除等导致的报错
                self.stdout.write(
                    self.style.WARNING(f"Failed to get detail of dev sandbox: {dev_sandbox.code}. Error: {e}")
                )
                continue

            url = f"{detail.urls.code_editor}/healthz"
            # 沙箱相关域名无法确定协议，因此全部遍历 http 和 https
            if self.is_alive(f"http://{url}") or self.is_alive(f"https://{url}"):
                self.stdout.write(self.style.SUCCESS(f"Dev sandbox {dev_sandbox.code} is alive"))
                dev_sandbox.renew_expired_at()

    def is_alive(self, url: str) -> bool:
        try:
            resp = requests.get(url, timeout=30)
            return resp.status_code == status.HTTP_200_OK and resp.json().get("status") == "alive"
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Dev sandbox status check failed for URL: {url}. Error: {e}"))
            return False
