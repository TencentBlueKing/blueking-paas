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
from typing import List

from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppResource, EnvVar
from paasng.platform.engine.constants import AppEnvName


class EnvVarsReader:
    """Read "configurations.env" from app model resource object

    :param res: App model resource object
    """

    def __init__(self, res: BkAppResource):
        self.res = res

    def read_all(self, env_name: AppEnvName) -> List[EnvVar]:
        """Read all env vars defined at given `env_name`

        :param env_name: Environment name
        :return: A list contains all env vars defined at given `env_name`, including `envOverlay`
        """
        env_vars = {}
        for env in self.res.spec.configuration.env:
            env_vars[env.name.upper()] = env.value

        if self.res.spec.envOverlay and self.res.spec.envOverlay.envVariables:
            for env_overlay in self.res.spec.envOverlay.envVariables:
                if env_overlay.envName == env_name:
                    env_vars[env_overlay.name.upper()] = env_overlay.value
        return [EnvVar(name=k, value=v) for k, v in env_vars.items()]
