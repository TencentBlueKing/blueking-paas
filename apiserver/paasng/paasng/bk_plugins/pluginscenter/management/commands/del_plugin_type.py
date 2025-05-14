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

from paasng.bk_plugins.pluginscenter.models import PluginDefinition, PluginInstance


class Command(BaseCommand):
    help = "删除指定的插件类型，插件类型下的所有插件都会被删除，谨慎操作！"

    def add_arguments(self, parser):
        parser.add_argument(
            "--id",
            dest="identifier",
            required=True,
            type=str,
            help=("插件类型ID"),
        )
        parser.add_argument("--no-dry-run", dest="dry_run", help="dry run", action="store_false")

    def handle(self, identifier, dry_run=True, *args, **options):
        if not PluginDefinition.objects.filter(identifier=identifier).exists():
            self.stdout.write(self.style.WARNING(f"ID 为 {identifier} 的插件类型不存在"))
            return

        del_plugin_count = PluginInstance.objects.filter(pd__identifier=identifier).count()
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"DRY-RUN: 删除插件类型：{identifier}， 关联的 {del_plugin_count} 个插件一起被删除")
            )
            return

        PluginDefinition.objects.filter(identifier=identifier).delete()
        self.stdout.write(
            self.style.SUCCESS(f"DRY-RUN: 删除插件类型：{identifier}， 关联的 {del_plugin_count} 个插件一起被删除")
        )
        return
