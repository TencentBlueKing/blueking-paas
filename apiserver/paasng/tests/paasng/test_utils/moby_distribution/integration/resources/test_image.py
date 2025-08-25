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

import gzip
import hashlib
import json
import tarfile

import docker
import pytest

from paasng.utils.moby_distribution.registry.exceptions import ResourceNotFound
from paasng.utils.moby_distribution.registry.resources.blobs import Blob
from paasng.utils.moby_distribution.registry.resources.image import ImageRef, LayerRef
from paasng.utils.moby_distribution.registry.resources.manifests import ManifestRef
from paasng.utils.moby_distribution.registry.resources.tags import Tags


class TestImageRef:
    def test_save(self, tmp_path, repo, reference, registry_client):
        image_filepath = tmp_path / "image.tar"
        ImageRef.from_image(from_repo=repo, from_reference=reference, client=registry_client).save(image_filepath)

        with tarfile.open(image_filepath) as tarball:
            local_manifest = json.load(tarball.extractfile("manifest.json"))  # type: ignore[arg-type]
            config_file = tarball.extractfile(local_manifest[0]["Config"])
            assert config_file is not None
            config = config_file.read()

        digest = hashlib.sha256(config).hexdigest()
        manifest_filepath = tmp_path / "manifest"
        Blob(repo=repo, client=registry_client, local_path=manifest_filepath).download(digest=f"sha256:{digest}")

        assert manifest_filepath.read_bytes() == config

    def test_from_tarball(self, tmp_path, repo, reference, temp_repo, temp_reference, registry_client):
        image_filepath = tmp_path / "image.tar"
        image1 = ImageRef.from_image(from_repo=repo, from_reference=reference, client=registry_client)
        image1.save(image_filepath)

        image2 = ImageRef.from_tarball(
            workplace=tmp_path,
            src=image_filepath,
            to_repo=temp_repo,
            to_reference=temp_reference,
            client=registry_client,
        )
        assert image1.image_json_str == image2.image_json_str
        assert image1.image_json.rootfs == image2.image_json.rootfs
        assert len(image1.layers) == len(image2.layers)
        for layer in image2.layers:
            content = layer.local_path.read_bytes()
            assert layer.size == len(content)
            assert f"sha256:{hashlib.sha256(content).hexdigest()}" == layer.digest

    def test_push_v2(self, repo, reference, temp_repo, temp_reference, registry_client):
        ref = ImageRef.from_image(
            from_repo=repo,
            from_reference=reference,
            to_repo=temp_repo,
            to_reference=temp_reference,
            client=registry_client,
        )

        with pytest.raises(ResourceNotFound):
            assert Tags(repo=temp_repo, client=registry_client).list() == []
        manifest = ref.push_v2()
        assert Tags(repo=temp_repo, client=registry_client).list() == [temp_reference]
        ManifestRef(repo=temp_repo, reference=temp_reference, client=registry_client).delete()
        assert Tags(repo=temp_repo, client=registry_client).list() == []

        for layer in manifest.layers:
            Blob(repo=temp_repo, digest=layer.digest, client=registry_client).delete()
        Blob(repo=temp_repo, digest=manifest.config.digest, client=registry_client).delete()

    def test_add_exists_layer(self, repo, reference, registry_client):
        ref = ImageRef.from_image(from_repo=repo, from_reference=reference, client=registry_client)
        ref.add_layer(ref.layers[0])
        image_json = ref.image_json
        assert ref.layers[0].digest == ref.layers[-1].digest
        assert image_json.rootfs.diff_ids[0] == image_json.rootfs.diff_ids[-1]

    def test_add_local_layer(self, tmp_path, repo, reference, registry_client):
        ref = ImageRef.from_image(from_repo=repo, from_reference=reference, client=registry_client)

        path = tmp_path / "layer.tar.gz"
        with tarfile.open(name=path, mode="w:gz"):
            pass

        content = path.read_bytes()
        digest = "sha256:" + hashlib.sha256(content).hexdigest()
        ref.add_layer(LayerRef(repo=repo, local_path=path, exists=False))
        image_json = ref.image_json
        assert ref.layers[-1].digest == digest
        assert "sha256:" + hashlib.sha256(gzip.decompress(content)).hexdigest() == image_json.rootfs.diff_ids[-1]

    def test_merge_layer_to_image(self, tmp_path, repo, reference, temp_reference, registry_client):
        ref = ImageRef.from_image(
            from_repo=repo,
            from_reference=reference,
            to_reference=temp_reference,
            client=registry_client,
        )

        path = tmp_path / "layer.tar.gz"
        with tarfile.open(name=path, mode="w:gz"):
            pass

        ref.add_layer(LayerRef(repo=repo, local_path=path, exists=False))
        manifest = ref.push_v2()

        assert sorted(Tags(repo=repo, client=registry_client).list()) == sorted([reference, temp_reference])
        Blob(repo=repo, digest=manifest.layers[-1].digest, client=registry_client).delete()
        Blob(repo=repo, digest=manifest.config.digest, client=registry_client).delete()
        ManifestRef(repo=repo, reference=temp_reference, client=registry_client).delete()


class TestAlpine:
    @pytest.fixture()
    def docker_cli(self):
        return docker.from_env()

    def test_push(self, registry_client, tmp_path, alpine_tar, docker_cli, registry_netloc):
        ref = ImageRef.from_tarball(
            workplace=tmp_path, src=alpine_tar, to_repo="alpine", to_reference="push", client=registry_client
        )
        ref.push()

        ImageRef.from_image(from_repo="alpine", from_reference="push", client=registry_client)
        assert (
            docker_cli.containers.run(f"{registry_netloc}/alpine:push", command="echo hello", remove=True)
            == b"hello\n"
        )

    def test_append(self, registry_client, tmp_path, alpine_tar, alpine_append_layer, docker_cli, registry_netloc):
        ref = ImageRef.from_tarball(
            workplace=tmp_path, src=alpine_tar, to_repo="alpine", to_reference="append", client=registry_client
        )
        ref.add_layer(LayerRef(local_path=alpine_append_layer))
        ref.push()

        ImageRef.from_image(from_repo="alpine", from_reference="append", client=registry_client)
        assert (
            docker_cli.containers.run(f"{registry_netloc}/alpine:append", command="cat /append/content", remove=True)
            == b"__flag__\n"
        )

    def test_append_gzip(
        self, registry_client, tmp_path, alpine_tar, alpine_append_gzip_layer, docker_cli, registry_netloc
    ):
        ref = ImageRef.from_tarball(
            workplace=tmp_path, src=alpine_tar, to_repo="alpine", to_reference="append-gzip", client=registry_client
        )
        ref.add_layer(LayerRef(local_path=alpine_append_gzip_layer))
        ref.push()

        ImageRef.from_image(from_repo="alpine", from_reference="append-gzip", client=registry_client)
        assert (
            docker_cli.containers.run(
                f"{registry_netloc}/alpine:append-gzip", command="cat /append/content", remove=True
            )
            == b"__flag__\n"
        )
