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
# Generated by Django 3.2.12 on 2023-05-30 08:13

from django.db import migrations
from paasng.platform.modules.helpers import ModuleRuntimeBinder


class LegacyModuleRuntimeManager:
    def __init__(self, module):
        self.module = module

    def get_slug_builder(self):
        """返回当前模块绑定的 AppSlugBuilder, 如果未绑定, 则返回 None"""
        # Tips: 模块与 Builder 实际上是 N-1 的关系
        builder = self.module.slugbuilders.last()
        return builder

    def get_slug_runner(self):
        # Tips: 模块与 Builder 实际上是 N-1 的关系
        runner = self.module.slugrunners.last()
        return runner

    def list_buildpacks(self):
        """返回当前模块绑定的 AppSlugBuilder"""
        # Tips: 模型与 AppSlugBuilder 是 N-N 的关系, 这里借助中间表的自增 id 进行排序

        return [
            relationship.appbuildpack
            for relationship in self.module.buildpacks.through.objects.filter(module=self.module)
            .order_by("id")
            .prefetch_related("appbuildpack")
        ]


def migrate_to_buildconfig(apps, schema_editor):
    """迁移 buildpacks/builder/runner 的绑定关系到 BuildConfig 模型"""
    Module = apps.get_model("modules", "Module")
    for module in Module.objects.all():
        mgr = LegacyModuleRuntimeManager(module)
        builder = mgr.get_slug_builder()
        runner = mgr.get_slug_runner()
        if builder is None or runner is None:
            # 当前模块未绑定 builder/runner
            continue
        buildpacks = mgr.list_buildpacks()
        binder = ModuleRuntimeBinder(module)
        binder.clear_runtime()
        binder.bind_image(slugrunner=runner, slugbuilder=builder)
        binder.bind_buildpacks(buildpacks, [bp.id for bp in buildpacks])


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0008_buildconfig'),
    ]

    operations = [
        migrations.RunPython(migrate_to_buildconfig)
    ]
