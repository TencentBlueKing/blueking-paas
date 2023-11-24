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
import typing

from django.core.management.base import BaseCommand
from django.db import transaction

from paasng.platform.modules.helpers import SlugbuilderBinder
from paasng.platform.modules.models import AppBuildPack, AppSlugBuilder


class Command(BaseCommand):
    help = "绑定 slugbuilder 和 buildpack"

    def add_arguments(self, parser):
        parser.add_argument("--image", dest="image", help="slugbuilder name")
        parser.add_argument("--buildpack", dest="buildpack_ids", type=int, help="buildpack id", nargs="*")
        parser.add_argument("--buildpack-name", dest="buildpack_names", help="buildpack name", nargs="*")
        parser.add_argument("--dry-run", dest="dry_run", help="dry run", action="store_true")

    def get_slugbuilder(self, image: str) -> AppSlugBuilder:
        """根据条件获取一个 slugbuilder 对象"""
        return AppSlugBuilder.objects.get(name=image)

    def get_buildpacks(
        self, buildpack_ids: typing.List[int], buildpack_names: typing.List[str]
    ) -> typing.Iterable[AppBuildPack]:
        """根据条件获取 buildpack queryset"""
        qs = AppBuildPack.objects.all()
        if buildpack_ids:
            qs = qs.filter(pk__in=buildpack_ids)
        if buildpack_names:
            qs = qs.filter(name__in=buildpack_names)
        return qs

    @transaction.atomic
    def handle(self, image, buildpack_ids, buildpack_names, dry_run, **kwargs):
        slugbuilder = self.get_slugbuilder(image)
        buildpacks = self.get_buildpacks(buildpack_ids, buildpack_names)
        binder = SlugbuilderBinder(slugbuilder)

        for buildpack in [bp for bp in buildpacks if bp.region == slugbuilder.region]:
            print(
                f"binding buildpack {buildpack.name}[{buildpack.pk}] to slugbuilder "
                f"{slugbuilder.name}[{slugbuilder.pk}]"
            )
            if not dry_run:
                binder.bind_buildpack(buildpack)
