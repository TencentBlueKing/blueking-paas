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

import json

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from paas_service.models import Plan


class Command(BaseCommand):
    help = "根据 plan fixture file 内容将增量信息更新到 plan config"

    def add_arguments(self, parser):
        parser.add_argument("--path", dest="path", help="plan fixture file path")

        parser.add_argument(
            "--no-dry-run",
            dest="dry_run",
            default=True,
            action="store_false",
            help="试运行模式（只显示变更不实际保存）",
        )

    def handle(self, path: str, dry_run: bool, **options):
        with open(path, "r") as f:
            plan_fixtures = json.load(f)

        for p in plan_fixtures:
            try:
                plan = Plan.objects.get(pk=p["pk"])
            except ObjectDoesNotExist:
                # 该命令只做更新操作
                # 因此如果没有找到对应的 Plan 对象，则跳过
                continue

            original_config = plan.config
            config = update_config_safely(json.loads(original_config), json.loads(p["fields"]["config"]))

            if not dry_run:
                plan.config = json.dumps(config)
                plan.save(update_fields=["config"])

            self.stdout.write(self.style.NOTICE(f"plan config 变化：\n before:{original_config} \n after:{config} \n"))


def update_config_safely(original_config: dict, new_config: dict) -> dict:
    """
    安全更新配置字典，只添加原配置中不存在的新字段，保留已有字段不变

    :param original_config: 原始配置字典，将被更新
    :param new_config: 包含新字段的配置

    :returns: 更新后的配置字典
    """
    for key, value in new_config.items():
        # 仅当原配置中不存在该键时，才添加新字段
        if key not in original_config:
            original_config[key] = value

    return original_config
