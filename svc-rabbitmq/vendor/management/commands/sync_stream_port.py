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

"""按方案配置回填/移除存量实例凭证中的 stream 端口

新实例由 Provider.create_instance 直接写入，本命令处理方案改配置前已开通的存量实例：
回填后应用重新部署即可拿到 RABBITMQ_STREAM_PORT，不需要解绑重绑。

用法::

    python manage.py sync_stream_port --dry-run           # 试运行，确认范围
    python manage.py sync_stream_port                     # 回填所有已开启 stream 的方案
    python manage.py sync_stream_port --plan-id <uuid>    # 只处理指定方案
    python manage.py sync_stream_port --remove            # 方案关闭 stream 后的清理
"""

import json

from django.core.management.base import BaseCommand
from paas_service.models import Plan, ServiceInstance

from vendor.constants import DEFAULT_STREAM_PORT


class Command(BaseCommand):
    help = "按方案配置回填/移除存量实例凭证中的 stream 端口（应用侧为 RABBITMQ_STREAM_PORT）"

    def add_arguments(self, parser):
        parser.add_argument("--plan-id", dest="plan_id", default=None, help="只处理指定方案，不填则处理全部方案")
        parser.add_argument("--remove", action="store_true", help="移除 stream 端口，用于方案关闭 stream 后的清理")
        parser.add_argument("--dry-run", dest="dry_run", action="store_true", help="试运行，只打印将变更的实例")

    def handle(self, plan_id: str, remove: bool, dry_run: bool, **options):
        plans = Plan.objects.filter(pk=plan_id) if plan_id else Plan.objects.all()

        changed = 0
        for plan in plans:
            config = plan.get_config()
            enabled = bool(config.get("enable_stream"))
            # --plan-id 指定单个方案时以用户意图为准；否则默认只回填已开启 stream 的方案，
            # --remove 只清理已关闭 stream 的方案
            if not plan_id and enabled == remove:
                continue

            port = config.get("stream_port") or DEFAULT_STREAM_PORT
            for instance in ServiceInstance.objects.filter(plan=plan, to_be_deleted=False):
                credentials = instance.get_credentials()
                if remove:
                    modified = credentials.pop("stream_port", None) is not None
                else:
                    modified = credentials.get("stream_port") != port
                    credentials["stream_port"] = port

                if not modified:
                    continue

                changed += 1
                action = "removed" if remove else f"set to {port}"
                self.stdout.write(f"{instance.uuid} (plan: {plan.name}) stream_port {action}")

                if not dry_run:
                    instance.credentials = json.dumps(credentials)
                    instance.save(update_fields=["credentials", "updated"])

        prefix = "待变更" if dry_run else "已变更"
        self.stdout.write(self.style.SUCCESS(f"{prefix} {changed} 个实例"))
