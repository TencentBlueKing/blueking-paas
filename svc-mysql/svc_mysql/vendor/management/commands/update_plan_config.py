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
import logging
from typing import Any, Dict

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from paas_service.models import Plan

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "根据 plan fixture file 内容将增量信息更新到 plan config"

    def add_arguments(self, parser):
        parser.add_argument("--path", dest="path", help="plan fixture file path")
        parser.add_argument(
            "--dry-run",
            dest="dry_run",
            action="store_true",
            help="试运行模式（只显示变更不实际保存）",
        )

    def handle(self, path: str, dry_run: bool, **options):
        with open(path, "r") as f:
            plan_cfgs = json.load(f)

        for cfg in plan_cfgs:
            try:
                plan = Plan.objects.get(pk=cfg["pk"])
            except ObjectDoesNotExist:
                # 该命令只做更新操作
                # 因此如果没有找到对应的 Plan 对象，则跳过
                logger.warning("skip updating plan config, plan not found, pk: %s", cfg["pk"])
                continue

            original_cfg = plan.config
            updated_cfg = update_dict_without_overwrite(json.loads(original_cfg), json.loads(cfg["fields"]["config"]))

            if not dry_run:
                plan.config = json.dumps(updated_cfg)
                plan.save(update_fields=["config", "updated"])

            self.stdout.write(
                self.style.NOTICE(f"plan config change: \n before:{original_cfg} \n after:{updated_cfg} \n")
            )


def update_dict_without_overwrite(base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    安全合并字典，仅添加基础字典不存在的新键值对

    :params base: 基础字典，已有键值将被保留
    :params updates: 提供需要合并的新键值对
    :return: 合并后的字典
    """
    return {**updates, **base}
