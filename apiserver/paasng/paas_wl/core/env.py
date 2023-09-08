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
from typing import Callable, Dict

from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import ModuleEnvironment

EnvIsRunningFunc = Callable[[ModuleEnvironment], bool]


class EnvIsRunningHub:
    """Get "is_running" property of env by different application type."""

    _map: Dict[str, EnvIsRunningFunc] = {}

    @classmethod
    def register_func(cls, type: ApplicationType, func: EnvIsRunningFunc):
        cls._map[type.value] = func

    @classmethod
    def get(cls, env: ModuleEnvironment) -> bool:
        """Check if an env is running, which mean a successful deployment is available
        for the env. This status is useful in many situations, such as creating a custom
        domain and etc.

        :param env: The environment object
        :return: Whether current env is running
        """
        app_type = env.application.type
        func = cls._map.get(app_type)
        if not func:
            raise RuntimeError(f'The "env_is_running" impl for {app_type} is not registered')
        return func(env)


def env_is_running(env: ModuleEnvironment) -> bool:
    return EnvIsRunningHub.get(env)
