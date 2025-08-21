# -*- coding: utf-8 -*-
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

from paasng.utils.moby_distribution.registry.client import DockerRegistryV2Client, default_client
from paasng.utils.moby_distribution.registry.utils import TypeTimeout, client_default_timeout


class RepositoryResource:
    def __init__(
        self,
        repo: str,
        client: DockerRegistryV2Client = default_client,
        *,
        timeout: TypeTimeout = client_default_timeout,
    ):
        self.repo = repo
        if client is not None:
            self._client = client
        self.timeout = timeout

    @property
    def client(self):
        if hasattr(self, "_client"):
            return self._client
        raise RuntimeError("Resource must bind Client")

    @client.setter
    def client(self, v: DockerRegistryV2Client):
        self._client = v
