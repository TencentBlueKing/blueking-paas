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
from django.db import transaction

from paasng.platform.modules.models import AppBuildPack
from paasng.platform.modules.utils import parse_assignment_list


class Command(BaseCommand):
    help = "管理 buildpack"

    def add_arguments(self, parser):
        parser.add_argument("-n", "--name", required=True, help="name")
        parser.add_argument("--display_name_zh_cn", required=False, help="buildpack display name(zh-cn)")
        parser.add_argument("--display_name_en", required=False, help="buildpack display name(en)")
        parser.add_argument("--description_zh_cn", required=False, help="buildpack description(zh-cn)")
        parser.add_argument("--description_en", required=False, help="buildpack description(en)")
        parser.add_argument("-t", "--tag", required=True, help="version")
        parser.add_argument("-l", "--language", required=True, help="language")
        parser.add_argument("-T", "--type", dest="type_", default="tar", help="type")
        parser.add_argument("-a", "--address", required=True, help="address")
        parser.add_argument("-r", "--region", required=True, dest="regions", help="available region name", nargs="+")
        parser.add_argument(
            "-e",
            "--environment",
            dest="environments",
            help="environment(k=v)",
            default=[],
            nargs="*",
        )
        parser.add_argument("--hidden", dest="is_hidden", help="is_hidden", action="store_true")

    @transaction.atomic
    def handle(
        self,
        name,
        display_name_zh_cn,
        display_name_en,
        description_zh_cn,
        description_en,
        regions,
        is_hidden,
        environments,
        tag,
        language,
        type_,
        address,
        **kwargs,
    ):
        for region in regions:
            buildpack_name = name.format(region=region)

            obj, created = AppBuildPack.objects.update_or_create(
                name=buildpack_name,
                region=region,
                defaults={
                    "display_name_zh_cn": display_name_zh_cn,
                    "display_name_en": display_name_en,
                    "description_zh_cn": description_zh_cn,
                    "description_en": description_en,
                    "is_hidden": is_hidden,
                    "version": tag,
                    "language": language,
                    "type": type_,
                    "address": address,
                    "environments": parse_assignment_list(environments),
                },
            )

            if created:
                self.stdout.write(f"created {AppBuildPack.__name__}[{obj.pk}] {buildpack_name}")
            else:
                self.stdout.write(f"updated {AppBuildPack.__name__}[{obj.pk}] {buildpack_name}")
