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
from typing import TYPE_CHECKING, Dict, Iterable, List, Optional

from django.db import transaction

from paas_wl.cluster.models import Cluster, Domain
from paas_wl.cluster.shim import EnvClusterService
from paasng.engine.constants import AppEnvName
from paasng.platform.modules.constants import APP_CATEGORY, ExposedURLType, SourceOrigin
from paasng.platform.modules.exceptions import BindError
from paasng.platform.modules.models import AppBuildPack, AppSlugBuilder, AppSlugRunner
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

    def __init__(self, module: 'Module', slugbuilder: Optional[AppSlugBuilder] = None):
        self.module = module
        self.slugbuilder = slugbuilder

    @transaction.atomic
    def bind_image(self, slugrunner: AppSlugRunner, slugbuilder: Optional[AppSlugBuilder] = None):
        """绑定构建和运行镜像,如果两个镜像的名称不一致将会报错"""
        slugbuilder = slugbuilder or self.slugbuilder
        self.slugbuilder = slugbuilder
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
        module.slugrunners.set([slugrunner], clear=True)

        # 同上，先清空已有的镜像
        module.slugbuilders.set([slugbuilder], clear=True)

    @transaction.atomic
    def unbind_image(self, slugrunner: AppSlugRunner, slugbuilder: Optional[AppSlugBuilder] = None):
        """解绑镜像"""
        if self.slugbuilder is None:
            return

        slugbuilder = slugbuilder or self.slugbuilder
        self.slugbuilder = slugbuilder
        module = self.module

        module.slugrunners.remove(slugrunner)
        module.slugbuilders.remove(slugbuilder)

    @transaction.atomic
    def bind_buildpack(self, buildpack: AppBuildPack):
        """绑定 Module/Slugbuilder/buildpack 三方关系"""
        slugbuilder = self.slugbuilder
        if slugbuilder is None:
            raise RuntimeError('slugbuilder is None')

        if slugbuilder.region != buildpack.region or not slugbuilder.buildpacks.filter(pk=buildpack.pk).exists():
            # 当前 slugbuilder 不能与当前 buildpack 建立关联
            raise BindError(
                f"binding between slugbuilder {slugbuilder.full_image} and buildpack {buildpack.name} is not allowed"
            )

        buildpack.modules.add(self.module)
        slugbuilder.modules.add(self.module)

    @transaction.atomic
    def unbind_buildpack(self, buildpack: AppBuildPack):
        """解绑 Module/Slugbuilder/buildpack 三方关系"""
        if self.slugbuilder is None:
            return

        buildpack.modules.remove(self.module)

    @transaction.atomic
    def clear_runtime(self):
        """清空所有运行时配置, 仅用于 bind 操作前"""
        self.module.buildpacks.clear()
        self.module.slugbuilders.clear()
        self.module.slugrunners.clear()

    @transaction.atomic
    def bind_buildpacks(self, buildpacks: Iterable[AppBuildPack]):
        """绑定多个 buildpack"""
        for buildpack in buildpacks:
            self.bind_buildpack(buildpack)

    def bind_buildpacks_by_name(self, names: List[str]):
        """根据给定的名称及顺序来绑定构建工具

        :raises: RuntimeError when no buildpacks can be found
        """
        if not self.slugbuilder:
            raise BindError("Can't bind buildpacks when without SlugBuilder")

        available_bps = {}
        for bp in self.slugbuilder.get_buildpack_choices(self.module, name__in=names):
            available_bps[bp.name] = bp

        buildpacks = []
        for name in names:
            try:
                buildpacks.append(available_bps[name])
            except KeyError:
                raise RuntimeError('No buildpacks can be found for name: {}'.format(name))

        self.bind_buildpacks(buildpacks)

    def bind_buildpacks_by_module_language(self):
        """根据模块的语言筛选可用的 buildpack 进行绑定"""
        assert self.slugbuilder
        # 选取指定语言的最新一个非隐藏的 buildpack
        buildpacks = self.slugbuilder.get_buildpack_choices(self.module, language=self.module.language)
        if not buildpacks:
            return
        buildpack = sorted(buildpacks, key=attrgetter("created"))[-1]
        self.bind_buildpack(buildpack)


class ModuleRuntimeManager:
    """模块相关运行时查询工具(NG)"""

    SECURE_ENCRYPTED_LABEL = "secureEncrypted"
    HTTP_SUPPORTED_LABEL = "supportHttp"

    def __init__(self, module: 'Module'):
        self.module = module

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
            return not str2bool(runner.get_label("supportHttp"))
        except Exception:
            return True

    def get_slug_builder(self, raise_exception: bool = True) -> AppSlugBuilder:
        """返回当前模块绑定的 AppSlugBuilder

        :param bool raise_exception: compatible with legacy app which don't bind any builder
        """
        # Tips: 模型与 Builder 实际上是 N-1 的关系
        builder = self.module.slugbuilders.last()
        if not builder and raise_exception:
            raise AppSlugBuilder.DoesNotExist("No builder bound")
        return builder

    def get_slug_runner(self, raise_exception: bool = True) -> AppSlugRunner:
        """返回当前模块绑定的 AppSlugRunner

        :param bool raise_exception: compatible with legacy app which don't bind any builder
        """
        # Tips: 模型与 Runner 实际上是 N-1 的关系
        runner = self.module.slugrunners.last()
        if not runner and raise_exception:
            raise AppSlugRunner.DoesNotExist("No runner bound")
        return runner

    def list_buildpacks(self) -> List[AppBuildPack]:
        """返回当前模块绑定的 AppSlugBuilder"""
        # Tips: 模型与 AppSlugBuilder 是 N-N 的关系, 这里借助中间表的自增 id 进行排序
        return [
            relationship.appbuildpack
            for relationship in self.module.buildpacks.through.objects.filter(module=self.module)
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
