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
import shlex
from typing import Dict, List, Optional

import cattr
from django.db import models
from jsonfield import JSONField
from translated_fields import TranslatedFieldWithFallback

from paas_wl.bk_app.cnative.specs.crd import bk_app
from paasng.platform.applications.models import Application
from paasng.platform.declarative.constants import AppDescPluginType
from paasng.platform.declarative.deployment.resources import SvcDiscovery
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
    """Config objects which describes deployment objects"""

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
            return {
                process.name: (shlex.join(process.command or []) + " " + shlex.join(process.args or [])).strip()
                for process in self.spec.processes
            }

        processes = self.runtime.get("processes", {})
        return {key: process["command"] for key, process in processes.items()}

    def get_processes(self) -> Dict[str, Dict[str, str]]:
        """get ProcessesTmpl

        ProcessesTmpl is a dict containing a process type and its corresponding ProcessTmpl"""
        processes = self.runtime.get("processes", {})
        return dict(processes.items())

    def get_deploy_hooks(self) -> HookList:
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
        if self.spec is not None:
            env_name = self.deployment.app_environment.environment
            env_variables = []
            for global_var in self.spec.configuration.env:
                env_variables.append(
                    {
                        "key": global_var.name,
                        "value": global_var.value,
                    }
                )
            if (env_overlay := self.spec.envOverlay) and (overlays := env_overlay.envVariables):
                for overlay in overlays:
                    if overlay.envName == env_name:
                        env_variables.append(
                            {
                                "key": overlay.name,
                                "value": overlay.value,
                            }
                        )
            return env_variables
        return self.env_variables

    @property
    def source_dir(self) -> str:
        return self.runtime.get("source_dir", "")
