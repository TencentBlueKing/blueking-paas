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

from typing import List, Optional

from paasng.utils.moby_distribution.registry.client import URLBuilder
from paasng.utils.moby_distribution.registry.resources import RepositoryResource
from paasng.utils.moby_distribution.registry.resources.manifests import ManifestRef
from paasng.utils.moby_distribution.spec.manifest import ManifestDescriptor


class Tags(RepositoryResource):
    def get(self, tag: str) -> Optional[ManifestDescriptor]:
        """retrieve the ManifestDescriptor identified by the tag."""
        return ManifestRef(self.repo, reference=tag, client=self.client, timeout=self.timeout).get_metadata()

    def untag(self, tag: str) -> bool:
        """Untag removes the provided tag association"""
        return ManifestRef(self.repo, reference=tag, client=self.client, timeout=self.timeout).delete()

    def list(self) -> List[str]:
        """return the list of tags in the repo"""
        url = URLBuilder.build_tags_url(self.client.api_base_url, self.repo)
        data = self.client.get(url=url, timeout=self.timeout).json()
        return data["tags"] or []
