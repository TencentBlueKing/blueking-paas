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

from django.dispatch import receiver

from paas_wl.bk_app.cnative.specs.resource import deploy_networking, get_mres_from_cluster, sync_networking
from paas_wl.workloads.networking.ingress.signals import cnative_custom_domain_updated
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.applications.signals import application_default_module_switch

logger = logging.getLogger(__name__)


@receiver(cnative_custom_domain_updated)
def on_custom_domain_updated(sender, env: ModuleEnvironment, **kwargs):
    """Trigger a new networking deploy."""
    deploy_networking(env)


@receiver(application_default_module_switch)
def sync_default_entrances_for_cnative_module_switching(sender, application, new_module, old_module, **kwargs):
    """sync module's default domains and subpaths after switching default module for cloud native app"""
    if application.type != ApplicationType.CLOUD_NATIVE:
        return

    for module in [old_module, new_module]:
        for env in module.envs.all():
            try:
                logger.info(f"Refreshing default entrances for {application.code}/{env.environment}/{module.name}...")
                if res := get_mres_from_cluster(env):
                    sync_networking(env, res)
            except Exception:
                logger.exception(
                    f"Error syncing default entrances for {application.code}/{env.environment}/{module.name}"
                )
