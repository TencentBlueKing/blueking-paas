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

import logging
from typing import Dict, Optional

from django.db import models
from jsonfield import JSONField
from translated_fields import TranslatedFieldWithFallback

from paasng.core.tenant.fields import tenant_id_field_factory
from paasng.platform.applications.models import Application
from paasng.platform.bkapp_model.entities import v1alpha2
from paasng.platform.declarative.constants import AppDescPluginType
from paasng.platform.engine.models.deployment import Deployment
from paasng.platform.modules.constants import DeployHookType
from paasng.platform.modules.models.deploy_config import HookList
from paasng.utils.models import OwnerTimestampedModel, TimestampedModel, make_json_field
from paasng.utils.structure import NotSetType

logger = logging.getLogger(__name__)


class ApplicationDescription(OwnerTimestampedModel):
    """Application description object"""

    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, db_constraint=False, related_name="declarative_config"
    )
    code = models.CharField(verbose_name="ID of application", max_length=20, db_index=True)
    name = TranslatedFieldWithFallback(models.CharField(verbose_name="application name", max_length=20))
    basic_info = JSONField(verbose_name="basic information", blank=True, default={})
    market = JSONField(verbose_name="market specs", blank=True, default={})
    modules = JSONField(verbose_name="modules specs", blank=True, default=[])
    plugins = JSONField(verbose_name="extra plugins", blank=True, default=[])
    is_creation = models.BooleanField(verbose_name="whether current description creates an application", default=False)
    tenant_id = tenant_id_field_factory()

    def get_plugin(self, plugin_type: AppDescPluginType) -> Optional[Dict]:
        """Return the first plugin in given type"""
        for plugin in self.plugins:
            if plugin["type"] == plugin_type.value:
                return plugin
        return None


BkAppSpecField = make_json_field("BkAppSpecField", v1alpha2.BkAppSpec)


class DeploymentDescription(TimestampedModel):
    """Config objects which describes deployment objects.

    TODO: 优化云原生应用的描述文件应用逻辑(具体问题详见下文)
    应用描述文件目前存在 2 类数据, 分别是可在页面上编辑的数据, 以及仅可通过应用描述文件提供的数据.

    对于仅可通过应用描述文件的数据, 在应用部署时会被 import_manifest 存储到实际生效的模型中, 例如
    - spec.processes -> ModuleProcessSpec
    - spec.hooks -> ModuleDeployHook
    - spec.svcDiscovery -> 由 EnvVariablesProviders 负责读取, 直接以环境变量形式注入到 spec.configuration.env.
        TODO: 目前的实现兼容普通应用, 对于云原生应用应该合并到 BkAppSpec 中的 spec.svcDiscovery 字段, 然后在创建的 configmap 中体现到这些配置？

    对于可在页面编辑的数据, 会在处理到相应资源时, 尝试从 DeploymentDescription 查询是否有在描述文件声明, 再根据业务逻辑做合并, 例如:
    - spec.configuration.env/spec.envOverlay.envVariables -> 由 EnvVarsReader 负责读取, 再与产品上配置的环境变量做合并.
        TODO: 由于 EnvVarsReader 丢失了环境属性, 导致云原生应用的拼接 BkAppSpec 时只能将环境变量放在 spec.configuration.env.
    """

    deployment = models.OneToOneField(
        Deployment, on_delete=models.CASCADE, db_constraint=False, related_name="declarative_config"
    )
    env_variables = JSONField(verbose_name="environment variables", blank=True, default=[])
    runtime = JSONField(verbose_name="runtime config", blank=True, default={})
    environments = JSONField(verbose_name="environment specified configs", blank=True, default={})
    plugins = JSONField(verbose_name="extra plugins", blank=True, default=[])

    spec: v1alpha2.BkAppSpec = BkAppSpecField(verbose_name="bkapp.spec", null=True, default=None)
    tenant_id = tenant_id_field_factory()

    def get_deploy_hooks(self) -> HookList:
        """从 spec 提取 hook 配置, 用于普通应用部署流程."""
        hooks = HookList()
        if self.spec is not None:
            _hooks = self.spec.hooks
            if _hooks and not isinstance(_hooks, NotSetType) and (pre_release_hook := _hooks.pre_release):
                hooks.upsert(
                    type_=DeployHookType.PRE_RELEASE_HOOK,
                    command=pre_release_hook.command or [],
                    args=pre_release_hook.args or [],
                )
        return hooks

    @property
    def source_dir(self) -> str:
        return self.runtime.get("source_dir", "")
