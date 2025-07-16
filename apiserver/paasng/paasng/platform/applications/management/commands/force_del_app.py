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

from blue_krill.data_types.enum import StrStructuredEnum
from django.core.management.base import BaseCommand

from paasng.accessories.publish.sync_market.utils import cascade_delete_legacy_app
from paasng.infras.iam.helpers import delete_builtin_user_groups, delete_grade_manager
from paasng.platform.applications.models import Application

logger = logging.getLogger(__name__)


class DelKeyType(StrStructuredEnum):
    """Source origin defines the origin of module's source code"""

    CODE = "code"
    NAME = "name"


class Command(BaseCommand):
    help = "强制删除应用鉴权信息。页面上删除应用时，会保留鉴权信息"

    def add_arguments(self, parser):
        parser.add_argument(
            "--type",
            dest="filter_key",
            default="code",
            required=False,
            type=str,
            help=("删除 key 的类型, code 或 name"),
            choices=[t.value for t in DelKeyType],
        )
        parser.add_argument(
            "-key",
            "--code-or-name-to-delete",
            dest="filter_value",
            type=str,
            required=True,
            help="The code or name to delete",
        )
        parser.add_argument("--dry-run", dest="dry_run", help="dry run", action="store_true")

    def handle(self, filter_key, filter_value, dry_run, *args, **options):
        """根据 code 或 name 强制删除应用鉴权信息。页面上删除应用时，会保留鉴权信息"""
        to_del_apps = Application.default_objects.filter(**{filter_key: filter_value})

        if not to_del_apps.exists():
            self.stdout.write(self.style.WARNING(f"{filter_key} 为 {filter_value} 的应用不存在"))
            return

        if to_del_apps.filter(is_deleted=False).exists():
            self.stdout.write(self.style.WARNING(f"{filter_key} 为 {filter_value} 的应用页面上还未删除，不能强制删除"))
            return

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"DRY-RUN: 删除 {filter_key} 为 {filter_value} 的应用鉴权信息"))
            return

        # 从 PaaS 2.0 中删除相关信息
        try:
            cascade_delete_legacy_app(filter_key, filter_value, False)
        except Exception as e:
            logger.exception(f"{filter_key} 为 {filter_value} 从 PaaS2.0 中删除失败.")
            self.stdout.write(self.style.ERROR(f"{filter_key} 为 {filter_value} 从 PaaS2.0 中删除失败: {e}"))
            return

        # 删除权限中心相关数据
        for app in to_del_apps:
            delete_builtin_user_groups(app.code)
            delete_grade_manager(app.code)

        # 从 PaaS 3.0 中删除相关的信息
        to_del_apps.delete()
        logger.info(f"{filter_key} 为 {filter_value} 的应用鉴权信息已经从 Application 表中删除")
        self.stdout.write(self.style.SUCCESS(f"{filter_key} 为 {filter_value} 的应用鉴权信息已经被强制删除成功"))
        return
