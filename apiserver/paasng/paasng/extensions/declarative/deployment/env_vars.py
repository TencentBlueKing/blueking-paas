# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
from typing import Dict

from paasng.engine.deploy.env_vars import env_vars_providers
from paasng.engine.models import Deployment
from paasng.extensions.declarative.models import DeploymentDescription


@env_vars_providers.register_deploy
def get_desc_env_variables(deployment: Deployment) -> Dict[str, str]:
    """Get env vars which were defined by deployment description file"""
    try:
        deploy_desc = DeploymentDescription.objects.get(deployment=deployment)
    except DeploymentDescription.DoesNotExist:
        return {}
    return EnvVariablesReader(deploy_desc).read_as_dict()


class EnvVariablesReader:
    """Reader for deployment's env variables"""

    def __init__(self, desc_obj: DeploymentDescription):
        self.desc_obj = desc_obj

    def read_as_dict(self) -> Dict[str, str]:
        """Read current env variables as dict"""
        result = {obj['key']: obj['value'] for obj in self.desc_obj.env_variables}
        return result
