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

from typing import Optional, Union

import libtrust

from paasng.utils.moby_distribution.registry.client import (
    DockerRegistryV2Client,
    URLBuilder,
    default_client,
)
from paasng.utils.moby_distribution.registry.exceptions import ResourceNotFound, UnSupportMediaType
from paasng.utils.moby_distribution.registry.resources import RepositoryResource
from paasng.utils.moby_distribution.registry.utils import (
    TypeTimeout,
    client_default_timeout,
    get_private_key,
)
from paasng.utils.moby_distribution.spec.manifest import (
    ManifestDescriptor,
    ManifestSchema1,
    ManifestSchema2,
    OCIManifestSchema1,
)


class ManifestRef(RepositoryResource):
    TYPES = {
        ManifestSchema1.content_type(): ManifestSchema1,
        ManifestSchema2.content_type(): ManifestSchema2,
        OCIManifestSchema1.content_type(): OCIManifestSchema1,
    }

    def __init__(
        self,
        repo: str,
        reference: str = "latest",
        client: DockerRegistryV2Client = default_client,
        *,
        timeout: TypeTimeout = client_default_timeout,
    ):
        super().__init__(repo, client, timeout=timeout)
        self.reference = reference

    def get(self, media_type: str = ManifestSchema2.content_type()):
        """retrieve image manifest as the provided media_type"""
        if media_type not in self.TYPES:
            raise UnSupportMediaType(media_type)

        type_ = self.TYPES[media_type]
        url = URLBuilder.build_manifests_url(self.client.api_base_url, self.repo, self.reference)
        headers = {"Accept": media_type}
        data = self.client.get(url=url, headers=headers, timeout=self.timeout).json()
        return type_(**data)

    def get_metadata(self, media_type: str = ManifestSchema2.content_type()) -> Optional[ManifestDescriptor]:
        """return ManifestDescriptor if the manifest exists."""
        if media_type not in self.TYPES:
            raise UnSupportMediaType(media_type)

        headers = {"Accept": media_type}
        url = URLBuilder.build_manifests_url(self.client.api_base_url, self.repo, self.reference)
        try:
            resp = self.client.head(url=url, headers=headers, timeout=self.timeout)
        except ResourceNotFound:
            return None

        media_type = resp.headers.get("Content-Type")
        digest = resp.headers.get("Docker-Content-Digest")
        size = resp.headers.get("Content-Length")

        return ManifestDescriptor(mediaType=media_type, digest=digest, size=size)

    def delete(self, raise_not_found: bool = True) -> bool:
        """Removes the manifest specified by the provided reference.

        Deleting a manifest that doesn't exist will raise ResourceNotFound if `raise_not_found` is true.
        Note that a manifest can only be deleted by digest,
        Therefore, delete a manifest will delete all tag associate with this manifest.
        """
        descriptor = self.get_metadata()
        if not descriptor:
            if raise_not_found:
                raise ResourceNotFound
            return False

        url = URLBuilder.build_manifests_url(self.client.api_base_url, self.repo, descriptor.digest)
        try:
            resp = self.client.delete(url=url, timeout=self.timeout)
        except ResourceNotFound:
            if raise_not_found:
                raise
            return False

        return resp.ok

    def put(self, manifest: Union[ManifestSchema1, ManifestSchema2, OCIManifestSchema1]) -> bool:
        """creates or updates the given manifest."""
        if isinstance(manifest, ManifestSchema1):
            resp = self._put_legacy_manifest(manifest)
        else:
            resp = self._put_new_manifest(manifest)

        return resp.ok

    def _put_legacy_manifest(self, manifest: ManifestSchema1):
        """put the docker schema 1 manifest with signed signature to the repository"""
        url = URLBuilder.build_manifests_url(self.client.api_base_url, self.repo, self.reference)
        private_key = get_private_key()
        data = manifest.json(
            include={
                "name",
                "tag",
                "architecture",
                "fsLayers",
                "history",
                "schemaVersion",
            },
        )
        js = libtrust.JSONSignature.new(data)
        js.sign(private_key)

        headers = {"Content-Type": manifest.content_type()}
        data = js.to_pretty_signature("signatures")
        return self.client.put(url=url, data=data, headers=headers, timeout=self.timeout)

    def _put_new_manifest(self, manifest: Union[ManifestSchema2, OCIManifestSchema1]):
        """put the docker schema 2 manifest or OCI manifest to the repository"""
        url = URLBuilder.build_manifests_url(self.client.api_base_url, self.repo, self.reference)
        headers = {"Content-Type": manifest.content_type()}
        data = manifest.json(
            exclude={
                "config": {"urls"},
                "layers": {"__all__": {"urls"}},
            }
        )
        return self.client.put(url=url, data=data, headers=headers, timeout=self.timeout)
