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

"""Use a separate module to avoid circular imports"""

from collections import OrderedDict
from typing import Callable

from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.engine.configurations.env_var.entities import EnvVariableList


def _make_id(target):
    if hasattr(target, "__func__"):
        return (id(target.__self__), id(target.__func__))
    return id(target)


class EnvVariablesProviders:
    """Allow registering extra env variables functions for applications"""

    def __init__(self):
        self._registered_funcs_env = OrderedDict()

    def register_env(self, func: Callable):
        """Register a function with env argument"""
        # Use id to avoid duplicated registrations
        self._registered_funcs_env[_make_id(func)] = func
        return func

    def gather(self, env: ModuleEnvironment) -> EnvVariableList:
        """Gather all env variables for given env

        :param deployment: if given, the result will include deployment-scoped env variables
        """
        result = EnvVariableList()
        for func in self._registered_funcs_env.values():
            result.extend(func(env))
        return result


env_vars_providers = EnvVariablesProviders()
