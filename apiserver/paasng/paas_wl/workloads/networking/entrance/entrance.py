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
from typing import TYPE_CHECKING, Dict, List

from paas_wl.workloads.networking.entrance.shim import LiveEnvAddresses, get_builtin_addr_preferred

if TYPE_CHECKING:
    from paasng.platform.applications.models import Application

logger = logging.getLogger(__name__)


def get_entrances(app: "Application") -> List[Dict]:
    """查询应用所有模块的访问入口"""
    all_entrances = []

    for module in app.modules.all():
        module_entrances = {"name": module.name, "is_default": module.is_default, "envs": {}}
        all_entrances.append(module_entrances)
        for env in module.envs.all():
            env_entrances = module_entrances["envs"].setdefault(env.environment, [])
            addresses = []
            # 每个环境仅展示一个内置访问地址
            is_running, builtin_address = get_builtin_addr_preferred(env)
            if builtin_address:
                addresses.append(builtin_address)
            elif not is_running:
                # No builtin address found for the not running env means there must
                # be something wrong with the platform config, log it.
                logger.error(
                    "cannot found builtin address, application: %s, module: %s(%s)",
                    app.code,
                    module.name,
                    env.environment,
                )
            else:
                # No builtin address found for the running env, this can be normal
                # when the module has no "web" process.
                pass

            addresses.extend(LiveEnvAddresses(env).list_custom())
            for address in addresses:
                env_entrances.append(
                    {
                        "module": module.name,
                        "env": env.environment,
                        "address": address,
                        "is_running": is_running,
                    }
                )
    return all_entrances
