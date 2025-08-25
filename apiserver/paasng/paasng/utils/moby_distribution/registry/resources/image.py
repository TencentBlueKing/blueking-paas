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
import io
import json
import logging
import shutil
import tarfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field

try:
    from pydantic import __version__ as pydantic_version
except ImportError:
    # pydantic <= 1.8.2 does not have __version__
    import pydantic as _pydantic

    pydantic_version = _pydantic.VERSION

from paasng.utils.moby_distribution.registry.client import DockerRegistryV2Client, default_client
from paasng.utils.moby_distribution.registry.resources import RepositoryResource
from paasng.utils.moby_distribution.registry.resources.blobs import Blob, HashSignWrapper
from paasng.utils.moby_distribution.registry.resources.manifests import ManifestRef
from paasng.utils.moby_distribution.registry.utils import (
    TypeTimeout,
    client_default_timeout,
    generate_temp_dir,
    parse_image,
)
from paasng.utils.moby_distribution.spec.image_json import History, ImageJSON, default_created
from paasng.utils.moby_distribution.spec.manifest import (
    DockerManifestConfigDescriptor,
    DockerManifestLayerDescriptor,
    ManifestSchema2,
)

logger = logging.getLogger(__name__)


class ImageManifest(BaseModel):
    config: str = Field(default="", alias="Config")
    RepoTags: List[str] = Field(default_factory=list)
    Layers: List[str] = Field(default_factory=list)


class LayerRef(BaseModel):
    repo: str = ""
    digest: str = ""
    size: int = -1
    exists: bool = False
    local_path: Optional[Path] = None


class ImageRef(RepositoryResource):
    """ImageRef is used to Manipulate Docker images"""

    def __init__(
        self,
        repo: str,
        reference: str,
        layers: List[LayerRef],
        initial_config: str,
        client: DockerRegistryV2Client = default_client,
        *,
        timeout: TypeTimeout = client_default_timeout,
    ):
        super().__init__(repo, client, timeout=timeout)
        self.reference = reference
        self.layers = layers
        self._initial_config = initial_config
        self._dirty = False
        # diff id is the digest of uncompressed tarball
        self._append_diff_ids: List[str] = []
        self._append_historys: List[History] = []

    @classmethod
    def from_image(
        cls,
        from_repo: str,
        from_reference: str,
        to_repo: Optional[str] = None,
        to_reference: Optional[str] = None,
        client: DockerRegistryV2Client = default_client,
    ):
        """Initial a `ImageRef` from `{from_repo}:{from_reference}` but will named it as `{to_repo, to_reference}`

        if no `to_repo` or `to_reference` given, use `from_repo` or `from_reference` as default.
        """
        if to_repo is None:
            to_repo = from_repo
        if to_reference is None:
            to_reference = from_reference
        manifest = ManifestRef(repo=from_repo, reference=from_reference, client=client).get(
            ManifestSchema2.content_type()
        )
        layers = [
            LayerRef(repo=from_repo, digest=layer.digest, size=layer.size, exists=True) for layer in manifest.layers
        ]

        fh = io.BytesIO()
        Blob(repo=from_repo, digest=manifest.config.digest, client=client, fileobj=fh).download()
        fh.seek(0)

        return cls(
            repo=to_repo,
            reference=to_reference,
            layers=layers,
            initial_config=fh.read().decode(),
            client=client,
        )

    @classmethod
    def from_tarball(
        cls,
        workplace: Path,
        src: Path,
        to_repo: Optional[str] = None,
        to_reference: Optional[str] = None,
        client: DockerRegistryV2Client = default_client,
    ):
        """Initial a `ImageRef` from a tarball locate in local disk, but will named it as `{to_repo, to_reference}`

        :param Path workplace: the workplace to extract the tarball and store gzip compressed layers
        :param Path src: the path of tarball
        :param str to_repo: the name for the image
        :param str to_reference: the tag for the image

        if no `to_repo` or `to_reference` given, will use RepoTags in `manifest.json`
        """
        with tarfile.open(name=src) as tarball:
            tarball.extractall(workplace)

            manifest_list = json.loads((workplace / "manifest.json").read_text())
            if not isinstance(manifest_list, list) or len(manifest_list) == 0:
                raise ValueError("Invalid manifest.json")

            manifest = ImageManifest(**manifest_list[0])
            if not manifest.RepoTags and (not to_repo or not to_reference):
                raise ValueError("Invalid repo or reference")

            named = parse_image(manifest.RepoTags[0])
            if to_repo is None:
                to_repo = named.name

            if to_reference is None:
                to_reference = named.tag or "latest"

            layers = []
            for layer in manifest.Layers:
                # gzip it for smaller size
                gzipped_filepath = workplace / (layer + ".gz")
                with (workplace / layer).open(mode="rb") as fh, gzip.open(gzipped_filepath, mode="wb") as compressed:
                    shutil.copyfileobj(fh, compressed)

                # The gzipped file can only be obtained after the compressed object is closed
                # (because the gzip context information has not yet been written).
                gzipped_signer = HashSignWrapper()
                with gzipped_filepath.open(mode="rb") as fh:
                    shutil.copyfileobj(fh, gzipped_signer)

                layers.append(
                    LayerRef(
                        repo=to_repo,
                        digest=gzipped_signer.digest(),
                        size=gzipped_signer.tell(),
                        local_path=gzipped_filepath,
                    )
                )

            return cls(
                repo=to_repo,
                reference=to_reference,
                layers=layers,
                initial_config=(workplace / manifest.config).read_text(),
                client=client,
            )

    def save(self, dest: str):
        """save the image to dest, as Docker Image Specification v1.2 Format

        spec: https://github.com/moby/moby/blob/master/image/spec/v1.2.md
        """
        manifest = ImageManifest(RepoTags=[f"{self.repo}:{self.reference}"])
        with generate_temp_dir() as workplace:
            # Step 1. save image json
            image_json_digest = hashlib.sha256(self.image_json_str.encode()).hexdigest()

            manifest.config = f"{image_json_digest}.json"
            (workplace / manifest.config).write_text(self.image_json_str)

            # Step 2. download layers
            for layer in self.layers:
                manifest.Layers.append(self._save_layer(workplace, layer=layer))

            # Step 3. save manifest
            (workplace / "manifest.json").write_text(f"[{manifest.json(by_alias=True)}]")

            # Step 4. save as tar
            with tarfile.open(mode="w", name=dest) as tarball:
                for f in workplace.iterdir():
                    tarball.add(name=str(f.absolute()), arcname=str(f.relative_to(workplace)))
        return dest

    def push(self, media_type: str = ManifestSchema2.content_type(), *, max_worker: int = 5):
        """push the image to the registry."""
        if media_type == ManifestSchema2.content_type():
            return self.push_v2(max_worker=max_worker)
        raise NotImplementedError("only support push images with Manifest Schema2.")

    def push_v2(self, *, max_worker: int = 5) -> ManifestSchema2:
        """push the image to the registry, with Manifest Schema2."""
        layer_descriptors_futures = []
        layer_descriptors = []
        # Step 1: upload all layers
        with ThreadPoolExecutor(max_workers=max_worker) as thread_pool:
            for layer in self.layers:
                layer_descriptors_futures.append(thread_pool.submit(self._upload_layer, layer))
        for future in layer_descriptors_futures:
            layer_descriptors.append(future.result())

        # Step 2: upload the image json
        config_descriptor = self._upload_config(self.image_json_str)

        # Step 3.: upload the manifest
        manifest = ManifestSchema2(config=config_descriptor, layers=layer_descriptors)
        ref = ManifestRef(
            repo=self.repo,
            reference=self.reference,
            client=self.client,
            timeout=self.timeout,
        )
        ref.put(manifest)
        if self._dirty:
            return ref.get(media_type=ManifestSchema2.content_type())
        return manifest

    def add_layer(self, layer: LayerRef, history: Optional[History] = None) -> DockerManifestLayerDescriptor:
        """Add a layer to this image.

        Step:
          1. calculate the sha256 sum for the gzipped_tarball, as digest
          2. calculate the sha256 sum for the uncompressed_tarball, as diff_id
        """
        if not layer.exists and not layer.local_path:
            raise ValueError("Unknown layer")

        uncompressed_tarball_signer = HashSignWrapper()
        # Add local layer
        if layer.local_path:
            # Step 1: calculate the sha256 sum for the tarball file
            raw_tarball_signer = HashSignWrapper()
            with layer.local_path.open(mode="rb") as gzipped:
                shutil.copyfileobj(gzipped, raw_tarball_signer)
                size = raw_tarball_signer.tell()

            # Step 2: calculate the sha256 sum for the uncompressed_tarball
            # for gzipped tarball, we need decompress first
            try:
                with gzip.open(filename=layer.local_path) as uncompressed:
                    shutil.copyfileobj(uncompressed, uncompressed_tarball_signer)
            except OSError:
                uncompressed_tarball_signer = raw_tarball_signer

            if layer.digest and layer.digest != raw_tarball_signer.digest():
                raise ValueError(
                    "Wrong digest, layer.digest<'%s'> != signer.digest<'%s'>",
                    layer.digest,
                    raw_tarball_signer.digest(),
                )

            layer.digest = raw_tarball_signer.digest()
            layer.repo = self.repo
            layer.size = size

        # Add remote layer if the layer is exists in registry
        else:
            with generate_temp_dir() as temp_dir:
                # Step 1: calculate the sha256 sum for the gzipped_tarball
                with (temp_dir / "blob").open(mode="wb") as fh:
                    raw_tarball_signer = HashSignWrapper(fh=fh)
                    Blob(
                        repo=layer.repo,
                        digest=layer.digest,
                        fileobj=raw_tarball_signer,
                        client=self.client,
                    ).download()
                    size = raw_tarball_signer.tell()

                # Step 2: calculate the sha256 sum for the uncompressed_tarball
                with gzip.open(filename=(temp_dir / "blob")) as uncompressed:
                    shutil.copyfileobj(uncompressed, uncompressed_tarball_signer)

            if layer.size != size:
                raise ValueError(
                    "Wrong Size, layer.size<'%d'> != signer.size<'%d'>",
                    layer.size,
                    size,
                )
            if layer.digest != raw_tarball_signer.digest():
                raise ValueError(
                    "Wrong digest, layer.digest<'%s'> != signer.digest<'%s'>",
                    layer.digest,
                    raw_tarball_signer.digest(),
                )

        self._dirty = True
        self._append_diff_ids.append(uncompressed_tarball_signer.digest())
        self._append_historys.append(
            history
            or History(
                comment="add by moby-distribution",
                created_by="add by moby-distribution",
                created=default_created(),
                empty_layer=False,
            )
        )
        self.layers.append(layer)

        return DockerManifestLayerDescriptor(
            digest=raw_tarball_signer.digest(),
            size=size,
        )

    @property
    def image_json(self) -> ImageJSON:
        base = ImageJSON(**json.loads(self._initial_config))
        if not self._dirty:
            return base
        base.rootfs.diff_ids.extend(self._append_diff_ids)
        base.history.extend(self._append_historys)
        return base

    @property
    def image_json_str(self) -> str:
        if not self._dirty:
            return self._initial_config
        image_json = self.image_json
        if pydantic_version.startswith("2."):
            return json.dumps(
                image_json.model_dump(mode="json", exclude_unset=True, exclude_defaults=True),  # type: ignore[attr-defined]
                separators=(",", ":"),
            )
        else:
            return image_json.json(exclude_unset=True, exclude_defaults=True, separators=(",", ":"))

    def _save_layer(self, workplace: Path, layer: LayerRef) -> str:
        """Download the gzipped layer, and uncompress as the raw tarball.

        if layer is exists in local disk(the local_path is not None), will skip download.

        :raise RequestErrorWithResponse: raise if an error occur.
        """
        gzip_path = layer.local_path or (workplace / "layers.tar.gz")
        temp_tarball_path = workplace / "layer.tar"

        if layer.local_path is None:
            Blob(
                repo=layer.repo,
                digest=layer.digest,
                local_path=gzip_path,
                client=self.client,
            ).download()

        with gzip.open(filename=gzip_path) as uncompressed, temp_tarball_path.open(mode="wb") as fh:
            signer = HashSignWrapper(fh)
            shutil.copyfileobj(uncompressed, signer)

        tarball_path = f"{signer.digest()}/layer.tar"
        (workplace / tarball_path).parent.mkdir(exist_ok=True, parents=True)

        if layer.local_path is None:
            gzip_path.unlink()

        shutil.move(
            str(temp_tarball_path.absolute()),
            str((workplace / tarball_path).absolute()),
        )
        return tarball_path

    def _upload_layer(self, layer: LayerRef) -> DockerManifestLayerDescriptor:
        """Upload the layer to the registry
        this func will mount the existed layers from other repo or upload the local layers to the repo.

        :raise RequestErrorWithResponse: raise if an error occur.
        """

        if layer.exists and layer.repo != self.repo:
            descriptor = Blob(repo=self.repo, digest=layer.digest, client=self.client).mount_from(from_repo=layer.repo)
        elif not layer.exists:
            blob = Blob(repo=self.repo, local_path=layer.local_path, client=self.client)
            descriptor = blob.upload()
        else:
            descriptor = Blob(repo=self.repo, client=self.client).stat(layer.digest)

        return DockerManifestLayerDescriptor(
            size=layer.size,
            digest=descriptor.digest,
            urls=descriptor.urls,
        )

    def _upload_config(self, image_json_str: str) -> DockerManifestConfigDescriptor:
        """Upload the Image JSON to the registry

        :raise RequestErrorWithResponse: raise if an error occur.
        """
        descriptor = Blob(
            repo=self.repo,
            fileobj=io.BytesIO(image_json_str.encode()),
            client=self.client,
        ).upload()
        return DockerManifestConfigDescriptor(
            size=len(image_json_str),
            digest=descriptor.digest,
            urls=descriptor.urls,
        )
