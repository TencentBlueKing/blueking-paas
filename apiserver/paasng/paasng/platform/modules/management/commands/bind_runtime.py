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

import typing

from django.core.management.base import BaseCommand
from django.db import transaction

from paasng.platform.modules.helpers import ModuleRuntimeBinder
from paasng.platform.modules.models import AppBuildPack, AppSlugBuilder, AppSlugRunner, Module


class Command(BaseCommand):
    help = "绑定模块运行时"

    def add_arguments(self, parser):
        parser.add_argument("--image", dest="image", help="image name")
        parser.add_argument("--buildpack", dest="buildpack_ids", type=int, help="buildpack id", nargs="*")
        parser.add_argument("--buildpack-name", dest="buildpack_names", help="buildpack name", nargs="*")
        parser.add_argument("--module", dest="module_names", help="module name", nargs="*")
        parser.add_argument("--app-code", dest="app_codes", help="application code", nargs="*")
        parser.add_argument("--dry-run", dest="dry_run", help="dry run", action="store_true")

    def get_slugbuilder(self, image: str) -> AppSlugBuilder:
        """根据条件获取一个 slugbuilder 对象"""
        return AppSlugBuilder.objects.get(name=image)

    def get_slugrunner(self, image: str) -> AppSlugRunner:
        """根据条件获取一个 slugrunner 对象"""
        return AppSlugRunner.objects.get(name=image)

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

    def get_modules(
        self, module_names: typing.List[str], application_codes: typing.List[str]
    ) -> typing.Iterable[Module]:
        """根据名称和 app code 筛选模块"""
        qs = Module.objects.all()
        if module_names:
            qs = qs.filter(name__in=module_names)
        if application_codes:
            qs = qs.filter(application__code__in=application_codes)
        return qs

    @transaction.atomic
    def handle(self, image, module_names, app_codes, buildpack_ids, buildpack_names, dry_run, **kwargs):
        modules = self.get_modules(module_names, app_codes)
        slugbuilder = self.get_slugbuilder(image)
        slugrunner = self.get_slugrunner(image)
        buildpacks = list(self.get_buildpacks(buildpack_ids, buildpack_names))

        for module in modules:
            binder = ModuleRuntimeBinder(module)
            print(
                f"binding slugbuilder {slugbuilder.name}[{slugbuilder.pk}] "
                f"and slugrunner {slugrunner.name}[{slugrunner.pk}] "
                f"to module {module.application.code}[{module.name}]"
            )
            if not dry_run:
                binder.bind_image(slugrunner, slugbuilder)

            for bp in buildpacks:
                print(f"binding buildpack {bp.name}[{bp.pk}] to module {module.application.code}[{module.name}]")
                if not dry_run:
                    binder.bind_buildpack(bp)
