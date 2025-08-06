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

from typing import TYPE_CHECKING

from django.conf import settings
from django.core.cache import cache
from django.db.models import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _

from paas_wl.infras.cluster.helm import HelmClient
from paas_wl.infras.cluster.shim import EnvClusterService
from paasng.accessories.publish.market.models import Product
from paasng.core.core.protections.base import BaseCondition, BaseConditionChecker
from paasng.core.core.protections.exceptions import ConditionNotMatched
from paasng.infras.iam.helpers import fetch_user_roles
from paasng.platform.applications.constants import AppEnvironment
from paasng.platform.bkapp_model.models import ModuleProcessSpec
from paasng.platform.engine.constants import DeployConditions, RuntimeType
from paasng.platform.environments.constants import EnvRoleOperation
from paasng.platform.environments.exceptions import RoleNotAllowError
from paasng.platform.environments.utils import env_role_protection_check
from paasng.platform.modules.models import Module
from paasng.platform.modules.specs import ModuleSpecs
from paasng.platform.sourcectl.exceptions import (
    AccessTokenForbidden,
    BasicAuthError,
    UserNotBindedToSourceProviderError,
)
from paasng.platform.sourcectl.source_types import get_sourcectl_types
from paasng.platform.sourcectl.version_services import get_version_service
from paasng.utils.basic import get_username_by_bkpaas_user_id

if TYPE_CHECKING:
    from bkpaas_auth.models import User

    from paasng.platform.applications.models import ModuleEnvironment


class DeployCondition(BaseCondition):
    def validate(self):
        raise NotImplementedError

    def __init__(self, user: "User", env: "ModuleEnvironment"):
        self.user = user
        self.env = env


class ProductInfoCondition(DeployCondition):
    """检查是否已经完善应用信息"""

    action_name = DeployConditions.FILL_PRODUCT_INFO.value

    def validate(self):
        if self.env.environment not in [AppEnvironment.PRODUCTION.value]:
            return
        if not Product.objects.filter(application=self.env.module.application).exists():
            raise ConditionNotMatched(_("未完善应用市场信息"), self.action_name)


class RepoAccessCondition(DeployCondition):
    """检查用户是否有该模块的源码仓库的访问权限"""

    def validate(self):
        try:
            # TODO: We should also check the return value.
            get_version_service(self.env.module, operator=self.user.pk).touch()
        except UserNotBindedToSourceProviderError as e:
            if not e.project:
                message = _("当前用户尚未授权访问仓库")
            else:
                message = _("当前用户尚未授权访问仓库: {source_type}").format(
                    source_type=get_sourcectl_types().get_choice_label(e.project.type)
                )

            action = DeployConditions.NEED_TO_BIND_OAUTH_INFO.value
            raise ConditionNotMatched(message, action) from e
        except AccessTokenForbidden as e:
            message = _("当前用户没有访问源码仓库的权限，请给 {repo} 授权").format(repo=e.fullname)
            action = DeployConditions.DONT_HAVE_ENOUGH_PERMISSIONS.value
            raise ConditionNotMatched(message, action) from e
        except BasicAuthError as e:
            message = _("当前账户没有访问源码仓库的权限，请确保账户名/密码正确")
            action = DeployConditions.NEED_TO_CORRECT_REPO_INFO.value
            raise ConditionNotMatched(message, action) from e
        except Exception as e:
            message = _("获取源码仓库信息失败，请确保仓库信息填写正确")
            action = DeployConditions.NEED_TO_CORRECT_REPO_INFO.value
            raise ConditionNotMatched(message, action) from e


class EnvProtectionCondition(DeployCondition):
    """检查该用户是否有该模块环境的部署权限"""

    action_name = DeployConditions.CHECK_ENV_PROTECTION.value

    def validate(self):
        roles = fetch_user_roles(self.env.application.code, get_username_by_bkpaas_user_id(self.user.pk))
        try:
            env_role_protection_check(operation=EnvRoleOperation.DEPLOY.value, env=self.env, roles=roles)
        except RoleNotAllowError as e:
            message = _("当前用户无部署该环境的权限, 请联系应用管理员")
            raise ConditionNotMatched(message, self.action_name) from e


class ProcfileCondition(DeployCondition):
    """检查是否已经完善进程启动命名"""

    action_name = DeployConditions.NEED_TO_COMPLETE_PROCFILE.value

    def validate(self):
        module: Module = self.env.module
        if ModuleSpecs(module).runtime_type != RuntimeType.CUSTOM_IMAGE:
            return

        if not ModuleProcessSpec.objects.filter(module=module).exists():
            raise ConditionNotMatched(_("未完善进程启动命令"), self.action_name)


class PluginTagValidationCondition(DeployCondition):
    """检查插件应用是否设置了分类"""

    action_name = DeployConditions.FILL_PLUGIN_TAG_INFO.value

    def validate(self):
        application = self.env.module.application
        if not application.is_plugin_app:
            return

        if self.env.environment not in [AppEnvironment.PRODUCTION.value]:
            return

        try:
            bk_plugin_profile = application.bk_plugin_profile
        except ObjectDoesNotExist:
            tag_info = None
        else:
            tag_info = bk_plugin_profile.get_tag_info()

        if not tag_info:
            raise ConditionNotMatched(_("未设置插件分类"), self.action_name)


class ApplicationExtraInfoCondition(DeployCondition):
    """检查是否已经完善应用分类或可用性保障信息"""

    action_name = DeployConditions.FILL_EXTRA_INFO.value

    def validate(self):
        app = self.env.module.application
        try:
            extra_info = app.extra_info
        except ObjectDoesNotExist:
            raise ConditionNotMatched(_("未完善应用基本信息"), self.action_name)

        if not extra_info.tag:
            raise ConditionNotMatched(_("未完善应用基本信息"), self.action_name)


class OperatorVersionCondition(DeployCondition):
    """检查 apiserver 和 operator 版本信息是否一致"""

    action_name = DeployConditions.CHECK_OPERATOR_VERSION.value

    def validate(self):
        # apiserver 根据 Helm 构建时, 注入容器 env
        apiserver_version = settings.APISERVER_VERSION

        # 仅在打开 检查开关的时候检查
        if not settings.APISERVER_OPERATOR_VERSION_CHECK or not apiserver_version:
            return

        # operator 通过 helm 客户端获取
        cluster_name = EnvClusterService(self.env).get_cluster_name()
        # 使用缓存
        cache_key = f"helm_release:{cluster_name}:operator_version"
        operator_version = cache.get(cache_key)
        if operator_version is None:
            operator_release = HelmClient(cluster_name).get_release("bkpaas-app-operator")
            operator_version = operator_release.chart.app_version if operator_release else None

            if operator_version == apiserver_version:
                # 通常 apiserver 会先于 operator 升级. 基于这一前提, 缓存时间设置为 24h, 进一步减少查询 helm release 的频次
                cache.set(cache_key, operator_version, 24 * 60 * 60)
                return

        if operator_version != apiserver_version:
            # 版本不一致时, 主动清理缓存, 促使下次强制刷新
            cache.delete(cache_key)
            message = _(
                "apiserver 与 operator 版本不一致，apiserver 版本: {apiserver_version}，operator 版本: {operator_version}".format(
                    apiserver_version=apiserver_version, operator_version=operator_version
                )
            )
            raise ConditionNotMatched(message, self.action_name)


class ModuleEnvDeployInspector(BaseConditionChecker):
    """Prepare to deploy a ModuleEnvironment"""

    condition_classes = [
        ProductInfoCondition,
        EnvProtectionCondition,
        RepoAccessCondition,
        ProcfileCondition,
        PluginTagValidationCondition,
        ApplicationExtraInfoCondition,
        OperatorVersionCondition,
    ]

    def __init__(self, user: "User", env: "ModuleEnvironment"):
        self.user = user
        self.env = env
        self.conditions = [cls(user, env) for cls in self.condition_classes]

    def __str__(self):
        return f"User<{self.user.username}> in Env{self.env}"


# Preparations for release end

try:
    from .protections_ext import register_extra_conditions

    register_extra_conditions()
except ImportError:
    pass
