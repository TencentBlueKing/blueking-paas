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

from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING, Any

from paas_service.base_vendor import ArgumentInvalidError

if TYPE_CHECKING:
    from .models import Cluster


class ClusterTagSelector:
    """根据 plan 配置中的 match_tags，从集群列表中筛选出拥有全部指定 ClusterTag 的集群。

    本类不对 ``match_tags`` 为空做特殊处理（空集合是任意标签集合的子集，``filter`` 会返回所有集群），
    空 ``match_tags`` 的业务语义由调用方决定（参见 ``vendor.provider.Provider.get_cluster_tag_selector``）。
    """

    def __init__(self, config: "Any"):
        if not isinstance(config, Mapping):
            raise ArgumentInvalidError("cluster_selector must be an object")

        values = config.get("match_tags") or []
        if not isinstance(values, list):
            raise ArgumentInvalidError("cluster_selector.match_tags must be a list")

        self.match_tags = {self.normalize_tag(value) for value in values}

    @staticmethod
    def normalize_tag(value: "Any") -> "str":
        """将配置中的标签规范化为 key=value 格式，并校验 key 和 value 均不为空。"""
        if not isinstance(value, str):
            raise ArgumentInvalidError("cluster_selector.match_tags must contain key=value strings")

        key, sep, tag_value = value.partition("=")
        key = key.strip()
        tag_value = tag_value.strip()
        if not sep or not key or not tag_value:
            raise ArgumentInvalidError(f"cluster_selector tag must use key=value format, not {value}")

        return f"{key}={tag_value}"

    def filter(self, clusters: "Iterable[Cluster]") -> "list[Cluster]":
        return [
            cluster
            for cluster in clusters
            if self.match_tags <= {f"{tag.key}={tag.value}" for tag in cluster.tags.all()}
        ]
