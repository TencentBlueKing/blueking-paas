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

from django.core.management.base import BaseCommand
from django.db import transaction

from paasng.platform.modules.models import AppSlugBuilder, AppSlugRunner
from paasng.platform.modules.utils import parse_assignment_list


class Command(BaseCommand):
    help = "管理运行时镜像"

    def add_arguments(self, parser):
        parser.add_argument('-n', '--name', required=True, dest="name", help="name")
        parser.add_argument('-r', '--region', required=True, dest="regions", help="available region name", nargs="+")
        parser.add_argument('--hidden', dest="is_hidden", help="is_hidden", action="store_true")
        parser.add_argument('--slugbuilder', required=False, help="slugbuilder image")
        parser.add_argument('--slugrunner', required=False, help="slugrunner image")
        parser.add_argument('--image', required=False, help="universal image")
        parser.add_argument('--display_name_zh_cn', required=False, help="image display name((zh_cn)")
        parser.add_argument('--display_name_en', required=False, help="image display name(en)")
        parser.add_argument('--description_zh_cn', required=False, help="image description(zh_cn)")
        parser.add_argument('--description_en', required=False, help="image description(en)")
        parser.add_argument(
            '-e',
            '--environment',
            dest="environments",
            help="environment(k=v)",
            default=[],
            nargs="*",
        )
        parser.add_argument(
            '-l',
            '--label',
            dest="labels",
            help="labels(k=v)",
            default=[],
            nargs="*",
        )

    @transaction.atomic
    def handle(
        self,
        name,
        image,
        slugbuilder,
        slugrunner,
        regions,
        is_hidden,
        display_name_zh_cn,
        display_name_en,
        description_zh_cn,
        description_en,
        environments,
        labels,
        **kwargs,
    ):

        slugbuilder = slugbuilder or image
        slugrunner = slugrunner or image

        for region in regions:
            image_name = name.format(region=region)
            self.update_or_create_image(
                AppSlugBuilder,
                image_name,
                region,
                slugbuilder,
                display_name_zh_cn,
                display_name_en,
                description_zh_cn,
                description_en,
                is_hidden,
                parse_assignment_list(environments),
                parse_assignment_list(labels),
            )
            self.update_or_create_image(
                AppSlugRunner,
                image_name,
                region,
                slugrunner,
                display_name_zh_cn,
                display_name_en,
                description_zh_cn,
                description_en,
                is_hidden,
                parse_assignment_list(environments),
                parse_assignment_list(labels),
            )

    def update_or_create_image(
        self,
        model,
        name,
        region,
        image,
        display_name_zh_cn,
        display_name_en,
        description_zh_cn,
        description_en,
        is_hidden,
        environments,
        labels,
    ):
        before, sep, after = image.rpartition(":")
        if not sep:
            tag = "latest"
        else:
            image, tag = before, after

        obj, created = model.objects.update_or_create(
            name=name,
            region=region,
            defaults={
                "is_hidden": is_hidden,
                "display_name_zh_cn": display_name_zh_cn,
                "display_name_en": display_name_en,
                "image": image,
                "tag": tag,
                "description_zh_cn": description_zh_cn,
                "description_en": description_en,
                "environments": environments,
                "labels": labels,
            },
        )

        if created:
            self.stdout.write(f"created {model.__name__}[{obj.pk}] {name}")
        else:
            self.stdout.write(f"updated {model.__name__}[{obj.pk}] {name}")
