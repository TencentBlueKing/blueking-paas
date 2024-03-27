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
from typing import Dict, List, Optional

import cattr
from django.db import models
from jsonfield import JSONField
from translated_fields import TranslatedFieldWithFallback

from paas_wl.bk_app.cnative.specs.crd import bk_app
from paasng.platform.applications.models import Application
from paasng.platform.declarative.constants import AppDescPluginType
from paasng.platform.declarative.deployment.resources import SvcDiscovery
from paasng.platform.engine.constants import ConfigVarEnvName
from paasng.platform.engine.models.deployment import Deployment
from paasng.platform.modules.constants import DeployHookType
from paasng.platform.modules.models.deploy_config import HookList
from paasng.utils.models import OwnerTimestampedModel, TimestampedModel, make_json_field
from paasng.utils.structure import register

logger = logging.getLogger(__name__)


BkAppSpecField = make_json_field("BkAppSpecField", register(bk_app.BkAppSpec))


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

    def get_plugin(self, plugin_type: AppDescPluginType) -> Optional[Dict]:
        """Return the first plugin in given type"""
        for plugin in self.plugins:
            if plugin["type"] == plugin_type.value:
                return plugin
        return None


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
    scripts = JSONField(verbose_name="scripts", blank=True, default={})
    environments = JSONField(verbose_name="environment specified configs", blank=True, default={})
    plugins = JSONField(verbose_name="extra plugins", blank=True, default=[])

    spec: bk_app.BkAppSpec = BkAppSpecField(verbose_name="bkapp.spec", null=True, default=None)

    def get_procfile(self) -> Dict[str, str]:
        """[Deprecated] get Procfile, should only be used to generate Procfile for buildpack

        Procfile is a dict containing a process type and its corresponding command
        """
        if self.spec is not None:
            return {process.name: process.get_proc_command() for process in self.spec.processes}

        processes = self.runtime.get("processes", {})
        return {key: process["command"] for key, process in processes.items()}

    def get_deploy_hooks(self) -> HookList:
        """从 spec 提取 hook 配置, 用于普通应用部署流程.

        > 存量的旧版本数据使用 `scripts` 字段
        """
        hooks = HookList()
        if self.spec is not None:
            if (_hooks := self.spec.hooks) and (pre_release_hook := _hooks.preRelease):
                hooks.upsert(
                    type_=DeployHookType.PRE_RELEASE_HOOK,
                    command=pre_release_hook.command or [],
                    args=pre_release_hook.args or [],
                )
            return hooks

        for key, value in self.scripts.items():
            try:
                type_ = DeployHookType(key)
            except ValueError:
                continue
            if value:
                hooks.upsert(type_, command=value)
        return hooks

    def get_svc_discovery(self) -> Optional[SvcDiscovery]:
        """从 spec 提取服务发现配置, 用于普通应用部署流程.

        > 存量的旧版本数据使用 `runtime`.`svc_discovery` 字段
        """
        if self.spec is not None:
            if svc_discovery := self.spec.svcDiscovery:
                return cattr.structure(
                    {
                        "bk_saas": [
                            {"bk_app_code": item.bkAppCode, "module_name": item.moduleName}
                            for item in svc_discovery.bkSaaS
                        ]
                    },
                    SvcDiscovery,
                )
            return None

        try:
            return cattr.structure(self.runtime["svc_discovery"], SvcDiscovery)
        except KeyError:
            return None
        except TypeError:
            logging.exception("Failed to parse SvcDiscovery, return None as fallback")
            return None

    def get_env_variables(self) -> List[Dict]:
        """从 spec 提供 dict 格式的环境变量给 EnvVariablesReader, 用于普通应用部署流程.

        > 存量的旧版本数据使用 `env_variables` 字段
        """
        if self.spec is not None:
            env_name = self.deployment.app_environment.environment
            env_variables = []
            for global_var in self.spec.configuration.env:
                env_variables.append(
                    {
                        "key": global_var.name,
                        "value": global_var.value,
                        "environment_name": ConfigVarEnvName.GLOBAL,
                    }
                )
            if (env_overlay := self.spec.envOverlay) and (overlays := env_overlay.envVariables):
                for overlay in overlays:
                    if overlay.envName == env_name:
                        env_variables.append(
                            {
                                "key": overlay.name,
                                "value": overlay.value,
                                "environment_name": env_name,
                            }
                        )
            return env_variables
        return self.env_variables

    @property
    def source_dir(self) -> str:
        return self.runtime.get("source_dir", "")
