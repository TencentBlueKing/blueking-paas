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

from django.dispatch import receiver

from paas_wl.core.env import env_is_running
from paas_wl.workloads.networking.ingress.shim import sync_subdomains, sync_subpaths
from paasng.platform.applications.signals import application_default_module_switch
from paasng.platform.modules.models import Module

logger = logging.getLogger(__name__)


@receiver(application_default_module_switch)
def sync_default_entrances_for_module_switching(sender, application, new_module, old_module, **kwargs):
    """sync module's default domains and subpaths after switching default module"""
    for module in [old_module, new_module]:
        try:
            logger.info(f"Refreshing domains and subpaths for {application.code}/{module.name}...")
            refresh_module_domains(module)
            refresh_module_subpaths(module)
        except Exception:
            logger.exception(f"Error syncing domains and subpaths for {application.code}/{module.name}")


def refresh_module_domains(module: Module):
    """Refresh a module's domains, you should call the function when module's exposed_url_type
    has been changed or application's default module was updated.
    """
    for env in module.envs.all():
        if not env_is_running(env):
            continue
        sync_subdomains(env)


def refresh_module_subpaths(module: Module) -> None:
    """Refresh a module's subpaths, you should call the function when module's exposed_url_type
    has been changed or application's default module was updated.
    """
    for env in module.envs.all():
        if not env_is_running(env):
            continue
        sync_subpaths(env)
