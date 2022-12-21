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
from typing import TYPE_CHECKING, Dict, List

from paasng.engine.controller.shortcuts import make_internal_client
from paasng.publish.entrance.utils import URL

if TYPE_CHECKING:
    from paasng.platform.applications.models import ModuleEnvironment
    from paasng.platform.modules.models import Module


class CustomDomainService:
    """Utilities: Application's custom domains"""

    def list_urls(self, env: 'ModuleEnvironment') -> List[URL]:
        """List an environment's all custom domains"""
        data = self._list_domains_data(env.module.application.code)
        valid_data = [d for d in data if d['environment_id'] == env.pk]
        return [self._to_url_obj(d['domain_url']) for d in valid_data]

    def list_urls_by_module(self, module: 'Module') -> List[URL]:
        """List a module's all custom domains"""
        data = self._list_domains_data(module.application.code)
        valid_data = [d for d in data if d['module_id'] == str(module.pk)]
        return [self._to_url_obj(d['domain_url']) for d in valid_data]

    def _list_domains_data(self, code: str) -> List:
        """List all domains data by application code"""
        return make_internal_client().list_custom_domains(code)

    @staticmethod
    def _to_url_obj(payload: Dict) -> URL:
        """Transform a domain_url payload into URL object"""
        return URL(
            protocol=payload['protocol'],
            hostname=payload['hostname'],
            port=payload['port'],
            # Use empty path for backward-compability
            path='',
        )
