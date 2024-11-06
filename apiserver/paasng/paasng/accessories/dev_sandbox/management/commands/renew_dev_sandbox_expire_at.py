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

import requests
from django.core.management.base import BaseCommand

from paas_wl.bk_app.dev_sandbox.controller import DevSandboxWithCodeEditorController
from paasng.accessories.dev_sandbox.models import DevSandbox

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "更新沙箱状态"

    def handle(self, *args, **options):
        for dev_sandbox in DevSandbox.objects.all():
            try:
                controller = DevSandboxWithCodeEditorController(
                    app=dev_sandbox.module.application,
                    module_name=dev_sandbox.module.name,
                    dev_sandbox_code=dev_sandbox.code,
                    owner=dev_sandbox.owner,
                )
            except Exception:
                # 防止沙箱资源被删除导致报错
                continue

            detail = controller.get_detail()
            url = detail.urls.code_editor_health_url if detail.urls is not None else None
            # 沙箱相关域名无法确定协议，因此全部遍历 http 和 https
            if url and (check_alive(f"http://{url}") or check_alive(f"https://{url}")):
                dev_sandbox.renew_expire_at()


def check_alive(url: str) -> bool:
    try:
        resp = requests.get(url)
        return resp.status_code == 200 and resp.json().get("status") == "alive"
    except Exception as e:
        logger.warning(f"Dev sandbox status check failed for URL: {url}. Error: {e}")
        return False
