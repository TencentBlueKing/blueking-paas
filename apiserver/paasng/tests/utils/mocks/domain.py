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

from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.modules.models import Module
from paasng.publish.entrance.utils import URL


class FakeCustomDomainService:
    """Utilities realted with application's custom domains"""

    def __init__(self):
        self._urls = []

    def __call__(self):
        """When the real DomainService type was replaced by an instance of current fake class, it can
        be useful to return `self` if client wants to create a new instance by calling the existing instance.
        """
        return self

    def list_urls(self, env: ModuleEnvironment) -> List[URL]:
        """List an environment's all custom domains"""
        return self._urls

    def list_urls_by_module(self, module: Module) -> List[URL]:
        """List a module's all custom domains"""
        return self._urls

    # fake utilities methods start

    def set_hostnames(self, hostnames: List[str]):
        self._urls = [URL(protocol='http', hostname=name, port=80, path='') for name in hostnames]
