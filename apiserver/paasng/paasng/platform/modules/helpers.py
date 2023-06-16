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
import logging
from operator import attrgetter
from typing import TYPE_CHECKING, Dict, Iterable, List, Optional, overload

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from paas_wl.cluster.models import Cluster, Domain
from paas_wl.cluster.shim import EnvClusterService
from paasng.engine.constants import AppEnvName
from paasng.platform.modules.constants import APP_CATEGORY, ExposedURLType, SourceOrigin
from paasng.platform.modules.exceptions import BindError, BuildPacksNotFound, BuildPackStackNotFound
from paasng.platform.modules.models import AppBuildPack, AppSlugBuilder, AppSlugRunner, BuildConfig
from paasng.utils.validators import str2bool

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from paasng.platform.modules.models import Module


class SlugbuilderBinder:
    """slugbuilder 和 buildpack 绑定工具"""

    def __init__(self, slugbuilder: AppSlugBuilder):
        self.slugbuilder = slugbuilder

    @transaction.atomic
    def bind_buildpack(self, buildpack: AppBuildPack):
        """绑定 slugbuilder 和 buildpack"""
        if self.slugbuilder.region != buildpack.region:
            raise BindError(
                f"region must be consistent between "
                f"slugbuilder({self.slugbuilder.full_image}) and buildpack({buildpack.pk})"
            )

        self.slugbuilder.buildpacks.add(buildpack)

    @transaction.atomic
    def unbind_buildpack(self, buildpack: AppBuildPack):
        """解绑 slugbuilder 和 buildpack"""
        self.slugbuilder.buildpacks.remove(buildpack)

    def set_buildpacks(self, buildpacks: List[AppBuildPack]):
        """将 slugbuilder 绑定的 buildpack 设置成指定的值"""
        for buildpack in buildpacks:
            if self.slugbuilder.region != buildpack.region:
                raise BindError(
                    f"region must be consistent between "
                    f"slugbuilder({self.slugbuilder.full_image}) and buildpack({buildpack.pk})"
                )
        self.slugbuilder.buildpacks.set(buildpacks, clear=True)


class ModuleRuntimeBinder:
    """模块相关运行时绑定工具"""

    def __init__(self, module: 'Module'):
        self.module = module
        self.build_config = BuildConfig.objects.get_or_create_by_module(module)

    @transaction.atomic
    def bind_bp_stack(self, bp_stack_name: str, ordered_bp_ids: List[int]):
        """绑定 buildpack stack - 即构建和运行的镜像、以及构建工具"""
        module = self.module
        try:
            slugbuilder = AppSlugBuilder.objects.filter_available(module=module).get(name=bp_stack_name)
            slugrunner = AppSlugRunner.objects.filter_available(module=module).get(name=bp_stack_name)
        except ObjectDoesNotExist:
            raise BuildPackStackNotFound(bp_stack_name)

        buildpacks = slugbuilder.get_buildpack_choices(module, id__in=ordered_bp_ids)
        if len(ordered_bp_ids) != len(buildpacks):
            raise BuildPacksNotFound

        self.clear_runtime()
        self.bind_image(slugrunner, slugbuilder)
        self.bind_buildpacks(buildpacks, ordered_bp_ids)

    @transaction.atomic
    def bind_image(self, slugrunner: AppSlugRunner, slugbuilder: AppSlugBuilder):
        """绑定构建和运行镜像,如果两个镜像的名称不一致将会报错"""
        module = self.module

        if slugbuilder is None:
            raise RuntimeError('slugbuilder is None')

        if slugrunner.name != slugbuilder.name:
            raise BindError(
                f"name must be consistent between "
                f"slugbuilder({slugbuilder.full_image}) and slugrunner({slugrunner.full_image})"
            )

        if slugbuilder.region != module.region:
            raise BindError(
                f"region must be consistent between " f"slugbuilder({slugbuilder.full_image}) and module({module.pk})"
            )

        if slugrunner.region != module.region:
            raise BindError(
                f"region must be consistent between " f"slugrunner({slugrunner.full_image}) and module({module.pk})"
            )

        # 当前模块只能使用一个镜像
        self.build_config.buildpack_builder = slugbuilder
        self.build_config.buildpack_runner = slugrunner
        self.build_config.save(update_fields=["buildpack_builder", "buildpack_runner", "updated"])

    @transaction.atomic
    def clear_runtime(self):
        """清空所有运行时配置, 仅用于 bind 操作前"""
        self.build_config.buildpacks.clear()
        self.build_config.buildpack_builder = None
        self.build_config.buildpack_runner = None
        self.build_config.save(update_fields=["buildpack_builder", "buildpack_runner", "updated"])

    @transaction.atomic
    def bind_buildpacks(self, buildpacks: Iterable[AppBuildPack], orders_bp_ids: List[int]):
        """绑定多个 buildpack"""
        for buildpack in self.get_ordered_buildpacks_list(buildpacks, orders_bp_ids):
            self.bind_buildpack(buildpack)

    @transaction.atomic
    def bind_buildpack(self, buildpack: AppBuildPack):
        """绑定 Module/Slugbuilder/buildpack 三方关系"""
        slugbuilder = self.build_config.buildpack_builder
        if slugbuilder is None:
            raise RuntimeError('slugbuilder is None')

        if slugbuilder.region != buildpack.region or not slugbuilder.buildpacks.filter(pk=buildpack.pk).exists():
            # 当前 slugbuilder 不能与当前 buildpack 建立关联
            raise BindError(
                f"binding between slugbuilder {slugbuilder.full_image} and buildpack {buildpack.name} is not allowed"
            )

        buildpack.related_build_configs.add(self.build_config)
        self.build_config.buildpack_builder = slugbuilder
        self.build_config.save(update_fields=["buildpack_builder", "updated"])

    def bind_buildpacks_by_name(self, names: List[str]):
        """根据给定的名称及顺序来绑定构建工具

        :raises: RuntimeError when no buildpacks can be found
        """
        slugbuilder = self.build_config.buildpack_builder
        if not slugbuilder:
            raise BindError("Can't bind buildpacks when without SlugBuilder")

        available_bps = {}
        for bp in slugbuilder.get_buildpack_choices(self.module, name__in=names):
            available_bps[bp.name] = bp

        buildpacks = []
        for name in names:
            try:
                buildpacks.append(available_bps[name])
            except KeyError:
                raise RuntimeError('No buildpacks can be found for name: {}'.format(name))

        if buildpacks:
            self.bind_buildpacks(buildpacks, [bp.id for bp in buildpacks])

    def bind_buildpacks_by_module_language(self):
        """根据模块的语言筛选可用的 buildpack 进行绑定"""
        slugbuilder = self.build_config.buildpack_builder
        if not slugbuilder:
            raise BindError("Can't bind buildpacks when without SlugBuilder")

        # 选取指定语言的最新一个非隐藏的 buildpack
        buildpacks = slugbuilder.get_buildpack_choices(self.module, language=self.module.language)
        if not buildpacks:
            return
        buildpack = sorted(buildpacks, key=attrgetter("created"))[-1]
        self.bind_buildpack(buildpack)

    @staticmethod
    def get_ordered_buildpacks_list(
        buildpacks: Iterable["AppBuildPack"], ordered_bp_ids: List[int]
    ) -> List['AppBuildPack']:
        """Get the ordered buildpacks list.

        :params buildpacks: the buildpacks list to be sorted
        :params ordered_bp_ids: ordered buildpack ids
        """
        bp_id_to_bp = {bp.id: bp for bp in buildpacks}
        return [bp_id_to_bp[i] for i in ordered_bp_ids]


class ModuleRuntimeManager:
    """模块相关运行时查询工具(NG)"""

    SECURE_ENCRYPTED_LABEL = "secureEncrypted"
    HTTP_SUPPORTED_LABEL = "supportHttp"
    CNB_LABEL = "isCloudNativeBuilder"

    def __init__(self, module: 'Module'):
        self.module = module
        self.build_config = BuildConfig.objects.get_or_create_by_module(module=self.module)

    @property
    def is_secure_encrypted_runtime(self) -> bool:
        """是否绑定了加密过的镜像"""

        try:
            # runner 和 builder 使用同一镜像，判断其中之一即可
            runner = self.get_slug_runner()
            return str2bool(runner.get_label(self.SECURE_ENCRYPTED_LABEL))
        except AppSlugRunner.DoesNotExist:
            logger.warning("failed to get slug runner, maybe not bind")
            return False
        except Exception:
            logger.warning("failed to get right runner and right label")
            return False

    @property
    def is_need_blobstore_env(self) -> bool:
        """描述当前模块绑定的运行时是否依赖对象存储相关的环境变量"""
        try:
            # runner 和 builder 使用同一镜像，判断其中之一即可
            runner = self.get_slug_runner()
        except AppSlugRunner.DoesNotExist:
            return True
        try:
            return not str2bool(runner.get_label(self.HTTP_SUPPORTED_LABEL))
        except Exception:
            return True

    @property
    def is_cnb_runtime(self) -> bool:
        """描述当前模块绑定的运行时是否使用 CloudNative Buildpacks 构建(构建产物为镜像)"""
        try:
            # runner 和 builder 使用同一镜像，判断其中之一即可
            runner = self.get_slug_runner()
        except AppSlugRunner.DoesNotExist:
            return False
        try:
            return str2bool(runner.get_label(self.CNB_LABEL))
        except Exception:
            return False

    @overload
    def get_slug_builder(self) -> AppSlugBuilder:
        ...

    @overload
    def get_slug_builder(self, raise_exception: bool = False) -> Optional[AppSlugBuilder]:
        ...

    def get_slug_builder(self, raise_exception: bool = True) -> Optional[AppSlugBuilder]:
        """返回当前模块绑定的 AppSlugBuilder

        :param bool raise_exception: compatible with legacy app which don't bind any builder
        """
        if not self.build_config.buildpack_builder and raise_exception:
            raise AppSlugBuilder.DoesNotExist("No runner bound")
        return self.build_config.buildpack_builder

    @overload
    def get_slug_runner(self) -> AppSlugRunner:
        ...

    @overload
    def get_slug_runner(self, raise_exception: bool = False) -> Optional[AppSlugRunner]:
        ...

    def get_slug_runner(self, raise_exception: bool = True) -> Optional[AppSlugRunner]:
        """返回当前模块绑定的 AppSlugRunner

        :param bool raise_exception: compatible with legacy app which don't bind any builder
        """
        if not self.build_config.buildpack_runner and raise_exception:
            raise AppSlugRunner.DoesNotExist("No runner bound")
        return self.build_config.buildpack_runner

    def list_buildpacks(self) -> List[AppBuildPack]:
        """返回当前模块绑定的 AppSlugBuilder"""
        # Tips: 模型与 AppSlugBuilder 是 N-N 的关系, 这里借助中间表的自增 id 进行排序

        return [
            relationship.appbuildpack
            for relationship in self.build_config.buildpacks.through.objects.filter(buildconfig=self.build_config)
            .order_by("id")
            .prefetch_related("appbuildpack")
        ]


def get_module_clusters(module: 'Module') -> Dict[AppEnvName, Cluster]:
    """return all cluster info of module envs"""
    return {AppEnvName(env.environment): EnvClusterService(env).get_cluster() for env in module.envs.all()}


def get_module_prod_env_root_domains(module: 'Module', include_reserved: bool = False) -> List[Domain]:
    """返回当前模块（生产环境）支持的所有根域名

    :param module: 模块
    :param include_reserved: 是否包括保留域名
    :raise ValueError: when module.exposed_url_type is None
    """
    prod_env = module.envs.filter(environment=AppEnvName.PROD).first()
    if not prod_env:
        return []

    cluster = EnvClusterService(prod_env).get_cluster()
    if module.exposed_url_type == ExposedURLType.SUBDOMAIN:
        root_domains = cluster.ingress_config.app_root_domains
    else:
        root_domains = cluster.ingress_config.sub_path_domains
    return [domain for domain in root_domains if include_reserved or not domain.reserved]


def get_image_labels_by_module(module: 'Module') -> Dict[str, str]:
    """根据 module 的属性获取筛选镜像的label"""
    # 目前需要根据模块的语言和类型（smart_app / legacy_app）等信息来筛选绑定的镜像
    labels = {"language": module.language}
    if module.source_origin == SourceOrigin.S_MART.value:
        labels["category"] = APP_CATEGORY.S_MART_APP.value
    else:
        labels["category"] = APP_CATEGORY.NORMAL_APP.value
    return labels
