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

import json

from paasng.utils.moby_distribution.registry.resources.blobs import Blob
from paasng.utils.moby_distribution.registry.resources.manifests import ManifestRef
from paasng.utils.moby_distribution.registry.resources.tags import Tags


def test_put_then_delete_v1(tmp_path, repo, reference, temp_reference, registry_client):
    manifest = ManifestRef(repo=repo, client=registry_client, reference=reference).get(
        "application/vnd.docker.distribution.manifest.v1+prettyjws"
    )

    manifest.tag = temp_reference
    ManifestRef(repo=repo, client=registry_client, reference=temp_reference).put(manifest)

    assert set(Tags(repo=repo, client=registry_client).list()) == {
        reference,
        temp_reference,
    }

    ManifestRef(repo=repo, client=registry_client, reference=temp_reference).delete()
    assert set(Tags(repo=repo, client=registry_client).list()) == {reference}


def test_put_then_delete_v2(tmp_path, repo, reference, temp_reference, registry_client):
    manifest = ManifestRef(repo=repo, client=registry_client, reference=reference).get(
        "application/vnd.docker.distribution.manifest.v2+json"
    )

    config_path = tmp_path / "config"
    blob = Blob(local_path=config_path, repo=repo, client=registry_client)

    # upload config
    blob.download(manifest.config.digest)
    config_path.write_text(json.dumps(json.loads(config_path.read_bytes()), indent=4))
    blob.upload()

    # upload manifest
    manifest.config.size = len(config_path.read_text())
    manifest.config.digest = blob.digest
    ManifestRef(repo=repo, client=registry_client, reference=temp_reference).put(manifest)

    assert set(Tags(repo=repo, client=registry_client).list()) == {
        reference,
        temp_reference,
    }

    ManifestRef(repo=repo, client=registry_client, reference=temp_reference).delete()
    assert set(Tags(repo=repo, client=registry_client).list()) == {reference}
