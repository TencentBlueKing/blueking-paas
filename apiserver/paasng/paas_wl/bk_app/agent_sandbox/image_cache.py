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

from dataclasses import dataclass, field
from functools import cached_property
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from paas_wl.infras.resources.base import crd
from paas_wl.infras.resources.base.exceptions import ResourceMissing

if TYPE_CHECKING:
    from kubernetes.dynamic import DynamicClient

# kube-fledged 默认使用的命名空间
KUBEFLEDGED_NAMESPACE = "kube-fledged"

# kube-fledged 使用的 API 版本
KUBEFLEDGED_API_VERSION = "kubefledged.io/v1alpha2"


@dataclass
class ImageCacheStatus:
    """ImageCache 的状态信息。

    :param status: 状态值，如 Succeeded, Failed, Processing 等。
    :param reason: 状态原因，如 ImageCacheRefresh, ImageCacheCreate 等。
    :param message: 状态详细信息描述。
    """

    status: str | None = None
    reason: str | None = None
    message: str | None = None


@dataclass
class ImageCache:
    """由 kube-fledged 管理的 ImageCache CRD，用于将镜像预拉取到集群节点。

    ImageCache 与具体的 PaaS 应用无关，固定创建在集群的 kube-fledged 命名空间。

    :param client: K8s API 客户端，用于操作目标集群。
    :param name: ImageCache 资源名称。
    :param images: 需要预拉取的镜像列表。
    :param image_pull_secrets: 拉取镜像所需的 Secret 名称列表（位于 kube-fledged 命名空间）。
    :param status: 从集群获取的状态信息，仅在 get 操作后填充。
    """

    client: "DynamicClient"
    name: str
    images: List[str] = field(default_factory=list)
    image_pull_secrets: List[str] = field(default_factory=list)
    status: ImageCacheStatus | None = None

    @cached_property
    def resource(self):
        """获取 ImageCache CRD 资源操作对象。"""
        return crd.ImageCache(self.client, api_version=KUBEFLEDGED_API_VERSION)

    def upsert(self):
        """在目标集群中创建或更新 ImageCache 资源。
        IMPORTANT: 更新时，一旦镜像列表发生变化，移除掉的镜像将会被 kube-fledged controller 直接强制删除，无论是否正在被使用 !!!
        """
        self.resource.create_or_update(
            name=self.name,
            namespace=KUBEFLEDGED_NAMESPACE,
            body=self._to_manifest(),
            update_method="patch",
            content_type="application/merge-patch+json",
        )

    def delete(self):
        """从目标集群中删除 ImageCache 资源。"""
        self.resource.delete(name=self.name, namespace=KUBEFLEDGED_NAMESPACE)

    def get(self) -> Optional["ImageCache"]:
        """从目标集群中获取 ImageCache 资源。

        :return: ImageCache 实例（包含 status 信息），若不存在则返回 None。
        """

        try:
            kube_data = self.resource.get(name=self.name, namespace=KUBEFLEDGED_NAMESPACE)
        except ResourceMissing:
            return None

        spec = kube_data.spec
        images: List[str] = []
        if cache_spec := getattr(spec, "cacheSpec", None):
            images = list(getattr(cache_spec[0], "images", None) or [])

        image_pull_secrets: List[str] = []
        for s in getattr(spec, "imagePullSecrets", None) or []:
            if name := getattr(s, "name", None):
                image_pull_secrets.append(name)

        status: Optional[ImageCacheStatus] = None
        if kube_status := getattr(kube_data, "status", None):
            status = ImageCacheStatus(
                status=getattr(kube_status, "status", None),
                reason=getattr(kube_status, "reason", None),
                message=getattr(kube_status, "message", None),
            )

        return ImageCache(
            name=self.name,
            client=self.client,
            images=images,
            image_pull_secrets=image_pull_secrets,
            status=status,
        )

    def _to_manifest(self) -> Dict[str, Any]:
        """生成 Kubernetes manifest 字典。"""
        body: Dict[str, Any] = {
            "apiVersion": KUBEFLEDGED_API_VERSION,
            "kind": "ImageCache",
            "metadata": {
                "name": self.name,
                "namespace": KUBEFLEDGED_NAMESPACE,
                "labels": {
                    "app": "kubefledged",
                    "kubefledged": "imagecache",
                },
            },
            "spec": {
                "cacheSpec": [
                    {
                        "images": self.images,
                    }
                ],
            },
        }

        if self.image_pull_secrets:
            body["spec"]["imagePullSecrets"] = [{"name": s} for s in self.image_pull_secrets]

        return body
