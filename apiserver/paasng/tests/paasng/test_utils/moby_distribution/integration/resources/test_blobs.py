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

import random
import string
from io import BytesIO

import pytest

from paasng.utils.moby_distribution.registry.exceptions import ResourceNotFound
from paasng.utils.moby_distribution.registry.resources.blobs import Blob
from paasng.utils.moby_distribution.registry.resources.manifests import ManifestRef


class TestBlob:
    def test_download(
        self,
        repo,
        reference,
        registry_client,
    ):
        ref = ManifestRef(repo=repo, reference=reference, client=registry_client)
        manifest = ref.get()

        fh = BytesIO()
        Blob(fileobj=fh, repo=repo, digest=manifest.config.digest, client=registry_client).download()
        fh.seek(0)
        assert fh.read()

    @pytest.mark.parametrize("method", ["upload", "upload_at_one_time"])
    def test_upload(self, repo, reference, registry_client, method):
        fh1 = BytesIO("".join(random.choices(string.ascii_letters, k=1024)).encode())

        blob = Blob(fileobj=fh1, repo=repo, client=registry_client)
        assert getattr(blob, method)()

        fh2 = BytesIO()
        Blob(fileobj=fh2, repo=repo, client=registry_client, digest=blob.digest).download()

        fh1.seek(0)
        fh2.seek(0)

        assert fh1.read() == fh2.read()

    def test_mount_from_and_delete(self, repo, reference, temp_repo, registry_client):
        ref = ManifestRef(repo=repo, reference=reference, client=registry_client)
        manifest = ref.get()

        fh1 = BytesIO()
        Blob(fileobj=fh1, repo=repo, digest=manifest.config.digest, client=registry_client).download()
        fh1.seek(0)

        assert Blob(repo=temp_repo, digest=manifest.config.digest, client=registry_client).mount_from(repo)

        fh2 = BytesIO()
        Blob(fileobj=fh2, repo=temp_repo, digest=manifest.config.digest, client=registry_client).download()
        fh2.seek(0)

        assert fh2.read() == fh1.read()

        Blob(repo=temp_repo, client=registry_client).delete(manifest.config.digest)
        with pytest.raises(ResourceNotFound):
            Blob(fileobj=fh2, repo=temp_repo, client=registry_client).download(digest=manifest.config.digest)
