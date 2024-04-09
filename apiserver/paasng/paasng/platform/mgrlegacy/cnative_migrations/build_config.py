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
from typing import List, Optional

from paasng.platform.applications.constants import ApplicationType
from paasng.platform.mgrlegacy.entities import BuildLegacyData, DefaultAppLegacyData
from paasng.platform.mgrlegacy.exceptions import PreCheckMigrationFailed
from paasng.platform.modules.helpers import ModuleRuntimeBinder
from paasng.platform.modules.manager import ModuleInitializer
from paasng.platform.modules.models import AppBuildPack, AppSlugBuilder, AppSlugRunner, BuildConfig

from .base import CNativeBaseMigrator


class BuildConfigMigrator(CNativeBaseMigrator):
    """BuildConfigMigrator to migrate the app all build config"""

    def _generate_legacy_data(self) -> Optional[DefaultAppLegacyData]:
        legacy_data: DefaultAppLegacyData = self.migration_process.legacy_data
        builds: List[BuildLegacyData] = []

        for m in self.app.modules.all():
            config = BuildConfig.objects.get_or_create_by_module(m)
            builds.append(
                BuildLegacyData(
                    module_name=m.name,
                    buildpack_ids=list(config.buildpacks.values_list("id", flat=True)),
                    buildpack_builder_id=config.buildpack_builder.id,
                    buildpack_runner_id=config.buildpack_runner.id,
                )
            )

        legacy_data.builds = builds
        return legacy_data

    def _can_migrate_or_raise(self):
        if self.app.type != ApplicationType.CLOUD_NATIVE.value:
            raise PreCheckMigrationFailed("type migrate must be called before build config migrate")

    def _migrate(self):
        """migrate buildpacks/buildpack_builder/buildpack_runner of the app(module)"""
        for m in self.app.modules.all():
            # 清理旧的构建信息
            binder = ModuleRuntimeBinder(m)
            binder.clear_runtime()
            # 重建运行时 build 关系
            # 如果云原生 cnb 支持了旧 buildpacks, 这里的迁移仅需处理 runner 和 builder 镜像的迁移?
            module_initializer = ModuleInitializer(m)
            module_initializer.bind_default_runtime()

    def _rollback(self):
        """rollback to legacy buildpacks/buildpack_builder/buildpack_runner"""
        builds: List[BuildLegacyData] = self.migration_process.legacy_data.builds
        build_map = {b.module_name: b for b in builds}

        for m in self.app.modules.all():
            # 清理旧的构建信息
            binder = ModuleRuntimeBinder(m)
            binder.clear_runtime()
            # 重新绑定旧构建信息
            binder.bind_image(
                slugrunner=AppSlugRunner.objects.get(id=build_map[m.name].buildpack_runner_id),
                slugbuilder=AppSlugBuilder.objects.get(id=build_map[m.name].buildpack_builder_id),
            )
            for bp_id in build_map[m.name].buildpack_ids:
                binder.bind_buildpack(AppBuildPack.objects.get(id=bp_id))
