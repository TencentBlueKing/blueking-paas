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

import datetime
import logging
from typing import TYPE_CHECKING, List, Optional, Tuple

from paasng.platform.sourcectl.models import AlternativeVersion, RepoBasicAuthHolder, VersionInfo
from paasng.platform.sourcectl.source_types import docker_registry_config
from paasng.utils.moby_distribution import APIEndpoint, DockerRegistryV2Client, ImageRef, Tags
from paasng.utils.text import remove_suffix

if TYPE_CHECKING:
    from paasng.platform.modules.models import Module


logger = logging.getLogger(__name__)
REGISTRY_ALIASES = {
    # Rewrite "docker.io" to the real endpoint "index.docker.io"
    "docker.io": "index.docker.io"
}
# 30 seconds timeout for list tags operation
TAG_LIST_TIMEOUT = 30


class DockerRegistryController:
    @classmethod
    def init_by_module(cls, module: "Module", operator: Optional[str] = None):
        source_obj = module.get_source_obj()
        repo_full_url = source_obj.get_repo_url()
        repo_fullname = source_obj.get_repo_fullname()

        if not repo_fullname or not repo_full_url:
            raise ValueError("Require repo to init DockerRegistryController")

        if repo_fullname == repo_full_url:
            # 一般情况下, 如果 image url 没有带上 registry, 那么默认的的 registry 就是 docker.io
            # 但是平台修改了这个限制, 默认的 registry 是配置中的 default_registry
            logger.warning("repo is missing `registry` part, using `default_registry` as endpoint")
            endpoint = docker_registry_config.default_registry
        else:
            endpoint = remove_suffix(repo_full_url, repo_fullname)

        try:
            holder = RepoBasicAuthHolder.objects.get_by_repo(module=module, repo_obj=source_obj)
            username, password = holder.basic_auth
        except RepoBasicAuthHolder.DoesNotExist:
            username = password = None

        return cls(
            endpoint=endpoint,
            repo=repo_fullname,
            username=username,
            password=password,
        )

    def __init__(
        self, endpoint: str, repo: str, username: Optional[str] = None, password: Optional[str] = None
    ) -> None:
        if "/" not in repo:
            # Docker Official Images is store in the namespace `library`
            logger.warning("repo does not contain namespace, guess it as `library`")
            repo = f"library/{repo}"
        endpoint = remove_suffix(endpoint, "/")
        self.endpoint = REGISTRY_ALIASES.get(endpoint, endpoint)
        self.repo = repo
        self._username = username
        self._password = password
        self._client: Optional[DockerRegistryV2Client] = None

    def touch(self) -> bool:
        client = self.get_client()
        return client.ping()

    def get_client(self, **kwargs) -> DockerRegistryV2Client:
        if self._client is None:
            self._client = DockerRegistryV2Client.from_api_endpoint(
                api_endpoint=APIEndpoint(url=self.endpoint), username=self._username, password=self._password
            )
        return self._client

    def extract_version_info(self, version_info: VersionInfo) -> Tuple[str, str]:
        return (version_info.version_name, version_info.revision)

    def list_alternative_versions(self) -> List[AlternativeVersion]:
        versions = []
        for tag in Tags(repo=self.repo, client=self.get_client(), timeout=TAG_LIST_TIMEOUT).list():
            versions.append(
                AlternativeVersion(
                    name=tag,
                    type="tag",
                    revision=tag,
                    url=f"{self.repo}:{tag}",
                    # 不支持获取时间
                    last_update=datetime.datetime.utcfromtimestamp(0),
                )
            )
        return versions

    def inspect_version(self, version_info: VersionInfo) -> AlternativeVersion:
        """查询指定版本的具体信息"""
        ref = ImageRef.from_image(from_repo=self.repo, from_reference=version_info.revision, client=self.get_client())
        return AlternativeVersion(
            name=version_info.revision,
            type="tag",
            revision=version_info.revision,
            url=f"{self.repo}:{version_info.revision}",
            last_update=ref.image_json.created,
            extra=ref.image_json.dict(include={"created", "author", "architecture", "os", "variant"}),
        )

    def extract_smart_revision(self, smart_revision: str) -> str:
        if ":" not in smart_revision:
            return smart_revision
        _, version_name = smart_revision.split(":")
        return version_name

    def build_url(self, version_info: VersionInfo) -> str:
        return f"{self.endpoint}/{self.repo}:{version_info.revision}"
