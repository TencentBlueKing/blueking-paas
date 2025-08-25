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

import hashlib
import json

import docker
import pytest

from paasng.utils.moby_distribution.registry.client import URLBuilder
from paasng.utils.moby_distribution.registry.resources.image import (
    ImageRef,
    LayerRef,
    ManifestSchema2,
)

try:
    from pydantic import __version__ as pydantic_version
except ImportError:
    # pydantic <= 1.8.2 does not have __version__
    import pydantic as _pydantic

    pydantic_version = _pydantic.VERSION
from paasng.utils.moby_distribution.registry.resources.manifests import ManifestRef, ManifestSchema1


@pytest.fixture()
def expected_fixture(request):
    return request.getfixturevalue(request.param)


class TestManifestRef:
    @pytest.mark.parametrize(
        ("media_type", "expected_fixture"),
        [
            (
                "application/vnd.docker.distribution.manifest.v1+prettyjws",
                "registry_manifest_schema1",
            ),
            (
                "application/vnd.docker.distribution.manifest.v2+json",
                "registry_manifest_schema2",
            ),
        ],
        indirect=["expected_fixture"],
    )
    def test_get(self, repo, reference, registry_client, media_type, expected_fixture):
        ref = ManifestRef(repo=repo, client=registry_client, reference=reference)
        assert ref.get(media_type).dict(exclude={"signatures"}, exclude_unset=True) == expected_fixture

    @pytest.mark.parametrize(
        ("media_type", "expected_fixture"),
        [
            (
                "application/vnd.docker.distribution.manifest.v1+prettyjws",
                "registry_manifest_schema1_metadata",
            ),
            (
                "application/vnd.docker.distribution.manifest.v2+json",
                "registry_manifest_schema2_metadata",
            ),
        ],
        indirect=["expected_fixture"],
    )
    def test_get_metadata(self, repo, reference, registry_client, media_type, expected_fixture):
        ref = ManifestRef(repo=repo, client=registry_client, reference=reference)

        if pydantic_version.startswith("2."):
            dumped = json.dumps(
                ref.get(media_type).model_dump(mode="json", exclude_unset=True),
                indent=3,
            )
        else:
            dumped = ref.get(media_type).json(indent=3, exclude_unset=True)
        descriptor = ref.get_metadata(media_type)

        assert descriptor is not None
        assert descriptor.dict(exclude_unset=True) == expected_fixture
        assert descriptor.size == len(dumped)

        if media_type != ManifestSchema1.content_type():
            assert descriptor.digest == f"sha256:{hashlib.sha256(dumped.encode()).hexdigest()}"


class TestIntegration:
    @pytest.fixture()
    def docker_cli(self):
        return docker.from_env()

    @pytest.fixture(autouse=True)
    def _init_image(
        self,
        registry_client,
        tmp_path,
        alpine_tar,
        alpine_append_layer,
        docker_cli,
        registry_netloc,
    ):
        ref = ImageRef.from_tarball(
            workplace=tmp_path,
            src=alpine_tar,
            to_repo="alpine",
            to_reference="manifest",
            client=registry_client,
        )
        ref.add_layer(LayerRef(local_path=alpine_append_layer))
        ref.push()

    def test_inspect(self, registry_client):
        url = URLBuilder.build_manifests_url(registry_client.api_base_url, repo="alpine", reference="manifest")
        headers = {"Accept": ManifestSchema2.content_type()}
        data = registry_client.get(url=url, headers=headers).json()
        assert data["config"].get("urls", []) == []
        for layer in data["layers"]:
            assert layer.get("urls", []) == []
