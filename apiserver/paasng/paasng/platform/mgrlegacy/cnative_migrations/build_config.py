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
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, List, Optional, Type

from paasng.platform.applications.constants import ApplicationType
from paasng.platform.engine.constants import RuntimeType
from paasng.platform.mgrlegacy.entities import BuildLegacyData, DefaultAppLegacyData
from paasng.platform.mgrlegacy.exceptions import PreCheckMigrationFailed
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.helpers import ModuleRuntimeBinder
from paasng.platform.modules.manager import ModuleInitializer
from paasng.platform.modules.models import AppBuildPack, AppSlugBuilder, AppSlugRunner, BuildConfig
from paasng.platform.modules.specs import SourceOriginSpecs

from .base import CNativeBaseMigrator

if TYPE_CHECKING:
    from paasng.platform.modules.models import Module


class BuildConfigMigrator(CNativeBaseMigrator):
    """BuildConfigMigrator to migrate the app all build config"""

    def _generate_legacy_data(self) -> Optional[DefaultAppLegacyData]:
        legacy_data: DefaultAppLegacyData = self.migration_process.legacy_data
        builds: List[BuildLegacyData] = []

        for m in self.app.modules.all():
            runtime_migrator = _ModuleRuntimeMigrator.get_by_module(m)
            builds.append(runtime_migrator.generate_legacy_data())

        legacy_data.builds = builds
        return legacy_data

    def _can_migrate_or_raise(self):
        if self.app.type != ApplicationType.CLOUD_NATIVE.value:
            raise PreCheckMigrationFailed(f"app({self.app.code}) type does not set to cloud_native")

    def _migrate(self):
        """migrate build config for the app(module)"""
        for m in self.app.modules.all():
            runtime_migrator = _ModuleRuntimeMigrator.get_by_module(m)
            runtime_migrator.migrate()

    def _rollback(self):
        """rollback to legacy build config"""
        builds: List[BuildLegacyData] = self.migration_process.legacy_data.builds
        build_map = {b.module_name: b for b in builds}

        for m in self.app.modules.all():
            runtime_migrator = _ModuleRuntimeMigrator.get_by_module(m)
            runtime_migrator.rollback(build_map[m.name])


class _ModuleRuntimeMigrator(ABC):
    _migrators: Dict[RuntimeType, Type["_ModuleRuntimeMigrator"]] = {}

    def __init__(self, module: "Module"):
        self.module = module

    def __init_subclass__(cls, **kwargs):
        if runtime_type := getattr(cls, "runtime_type", None):
            cls._migrators[runtime_type] = cls

    @classmethod
    def get_by_module(cls, module: "Module") -> "_ModuleRuntimeMigrator":
        source_origin = SourceOrigin(module.get_source_origin())
        source_origin_specs = SourceOriginSpecs.get(source_origin)

        if not (runtime_type := getattr(source_origin_specs, "runtime_type", None)):
            runtime_type = RuntimeType(BuildConfig.objects.get_or_create_by_module(module).build_method)

        try:
            return cls._migrators[runtime_type](module)
        except KeyError:
            raise NotImplementedError(f"no migrator for runtime_type({runtime_type})")

    @abstractmethod
    def generate_legacy_data(self) -> BuildLegacyData:
        """generate legacy data"""

    @abstractmethod
    def migrate(self):
        """migrate runtime config for the app(module)"""

    @abstractmethod
    def rollback(self, legacy_data: BuildLegacyData):
        """rollback to legacy runtime config"""


class _BuildPackMigrator(_ModuleRuntimeMigrator):
    """buildpack(slug-pilot) 应用运行时迁移器"""

    runtime_type = RuntimeType.BUILDPACK

    def generate_legacy_data(self) -> BuildLegacyData:
        config = BuildConfig.objects.get_or_create_by_module(self.module)

        buildpack_builder = config.buildpack_builder
        buildpack_runner = config.buildpack_runner
        if not buildpack_builder or not buildpack_runner:
            raise ValueError(f"no buildpacks bound to module({self.module.name})")

        return BuildLegacyData(
            module_name=self.module.name,
            buildpack_ids=list(config.buildpacks.values_list("id", flat=True)),
            buildpack_builder_id=buildpack_builder.id,
            buildpack_runner_id=buildpack_runner.id,
        )

    def migrate(self):
        """migrate the module's buildpacks/buildpack_builder/buildpack_runner"""
        # 清理旧的构建信息
        binder = ModuleRuntimeBinder(self.module)
        binder.clear_runtime()
        # 重建运行时 build 关系
        # 如果云原生 cnb 支持了旧 buildpacks, 这里的迁移仅需处理 runner 和 builder 镜像的迁移?
        module_initializer = ModuleInitializer(self.module)
        module_initializer.bind_default_runtime()

    def rollback(self, legacy_data: BuildLegacyData):
        """rollback to legacy buildpacks/buildpack_builder/buildpack_runner"""
        # 清理旧的构建信息
        binder = ModuleRuntimeBinder(self.module)
        binder.clear_runtime()
        # 重新绑定旧构建信息
        binder.bind_image(
            slugrunner=AppSlugRunner.objects.get(id=legacy_data.buildpack_runner_id),
            slugbuilder=AppSlugBuilder.objects.get(id=legacy_data.buildpack_builder_id),
        )
        for bp_id in legacy_data.buildpack_ids or []:
            binder.bind_buildpack(AppBuildPack.objects.get(id=bp_id))


class _ImageRegistryMigrator(_ModuleRuntimeMigrator):
    """旧镜像应用运行时迁移器"""

    runtime_type = RuntimeType.CUSTOM_IMAGE

    def generate_legacy_data(self) -> BuildLegacyData:
        return BuildLegacyData(
            module_name=self.module.name,
            source_origin=self.module.get_source_origin().value,
            source_repo_id=self.module.source_repo_id,
            source_type=self.module.source_type,
        )

    def migrate(self):
        """migrate the module's image_repository/build_method/source_config"""
        config = BuildConfig.objects.get_or_create_by_module(self.module)
        config.image_repository = self.module.get_source_obj().get_repo_url()
        config.build_method = RuntimeType.CUSTOM_IMAGE.value
        config.save(update_fields=["image_repository", "build_method"])

        self.module.source_repo_id = None
        self.module.source_type = None
        self.module.source_origin = SourceOrigin.CNATIVE_IMAGE.value
        self.module.save(update_fields=["source_repo_id", "source_type", "source_origin"])

    def rollback(self, legacy_data: BuildLegacyData):
        """rollback to legacy image_repository/build_method/source_config"""
        self.module.source_repo_id = legacy_data.source_repo_id
        self.module.source_type = legacy_data.source_type
        self.module.source_origin = legacy_data.source_origin
        self.module.save(update_fields=["source_repo_id", "source_type", "source_origin"])

        # 旧镜像应用的 build_method 默认为 buildpack
        BuildConfig.objects.filter(module=self.module).update(
            image_repository=None, build_method=RuntimeType.BUILDPACK.value
        )
