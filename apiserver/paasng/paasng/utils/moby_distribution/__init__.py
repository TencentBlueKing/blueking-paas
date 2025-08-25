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


# Moby Distribution upstream repo/version for traceability
# moby_distribution
# repo: https://github.com/shabbywu/distribution
# version: 0.8.2

from paasng.utils.moby_distribution.registry.client import (
    DockerRegistryV2Client,
    default_client,
    set_default_client,
)
from paasng.utils.moby_distribution.registry.resources.blobs import Blob
from paasng.utils.moby_distribution.registry.resources.image import ImageRef, LayerRef
from paasng.utils.moby_distribution.registry.resources.manifests import ManifestRef
from paasng.utils.moby_distribution.registry.resources.tags import Tags
from paasng.utils.moby_distribution.spec.endpoint import OFFICIAL_ENDPOINT, APIEndpoint
from paasng.utils.moby_distribution.spec.image_json import ImageJSON
from paasng.utils.moby_distribution.spec.manifest import (
    ManifestSchema1,
    ManifestSchema2,
    OCIManifestSchema1,
)

__all__ = [
    "DockerRegistryV2Client",
    "Blob",
    "ManifestRef",
    "Tags",
    "APIEndpoint",
    "OFFICIAL_ENDPOINT",
    "ManifestSchema1",
    "ManifestSchema2",
    "OCIManifestSchema1",
    "ImageJSON",
    "ImageRef",
    "LayerRef",
    "default_client",
    "set_default_client",
]
