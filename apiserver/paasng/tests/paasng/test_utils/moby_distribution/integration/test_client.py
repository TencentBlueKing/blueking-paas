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

from paasng.utils.moby_distribution.registry.client import (
    DockerRegistryV2Client,
    URLBuilder,
    default_client,
    set_default_client,
)
from paasng.utils.moby_distribution.spec.endpoint import OFFICIAL_ENDPOINT


class TestDockerRegistryV2Client:
    def test_ping(self, registry_client):
        assert registry_client.ping()

    def test_set_default_client(self, registry_client, registry_endpoint):
        set_default_client(registry_client)
        assert default_client.api_base_url == registry_endpoint

    def test_from_api_endpoint(self):
        set_default_client(DockerRegistryV2Client.from_api_endpoint(OFFICIAL_ENDPOINT))

        assert default_client.api_base_url == "https://" + OFFICIAL_ENDPOINT.api_base_url


class TestURLBuilder:
    def test_build_v2_url(self):
        assert URLBuilder.build_v2_url("mock://a") == "mock://a/v2/"

    def test_build_blobs_url(self):
        assert URLBuilder.build_blobs_url("mock://a", "b", "c") == "mock://a/v2/b/blobs/c"

    def test_build_manifests_url(self):
        assert URLBuilder.build_manifests_url("mock://a", "b", "c") == "mock://a/v2/b/manifests/c"

    def test_build_upload_blobs_url(self):
        assert URLBuilder.build_upload_blobs_url("mock://a", "b") == "mock://a/v2/b/blobs/uploads/"

    def test_build_tags_url(self):
        assert URLBuilder.build_tags_url("mock://a", "b") == "mock://a/v2/b/tags/list"
