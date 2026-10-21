# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

import posixpath
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from paas_wl.workloads.release_controller.constants import ImagePullPolicy


@dataclass
class ContainerRuntimeSpec:
    """The runtime specification of a container which contains image, command and
    other info. Used for building Command and SlugBuilderTemplate.
    """

    image: str
    # The actual command for starting the container
    command: Optional[List[str]] = None
    args: Optional[List[str]] = None
    envs: Dict[str, str] = field(default_factory=dict)
    image_pull_policy: ImagePullPolicy = field(default=ImagePullPolicy.IF_NOT_PRESENT)
    image_pull_secrets: List[Dict[str, str]] = field(default_factory=list)
    # The resources required by the container
    # e.g. {"limits": {"cpu": "1", "memory": "1Gi"}, "requests": {"cpu": "1", "memory": "1Gi"}}
    resources: Dict[str, Dict[str, str]] = field(default_factory=dict)


@dataclass(frozen=True)
class SecretFileMount:
    """将 Secret 中指定的 key 以只读文件的形式挂载到主容器

    每个 sub_path 对应 Secret 的一个 key，挂载为 `{mount_dir}/{sub_path}` 文件（使用 subPath）。
    只挂载到主容器，不影响 sidecar 容器。
    """

    volume_name: str
    secret_name: str
    mount_dir: str
    sub_paths: tuple[str, ...]

    def to_volume(self) -> Dict[str, Any]:
        """Pod 级别的 volume 定义"""
        return {"name": self.volume_name, "secret": {"secretName": self.secret_name}}

    def to_volume_mounts(self) -> List[Dict[str, Any]]:
        """主容器的 volumeMounts 定义，每个文件以只读 subPath 方式挂载"""
        return [
            {
                "name": self.volume_name,
                "mountPath": posixpath.join(self.mount_dir, sub_path),
                "subPath": sub_path,
                "readOnly": True,
            }
            for sub_path in self.sub_paths
        ]
