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

import os
from collections import defaultdict
from typing import Dict, Iterable, List, Optional

import yaml
from django.db.models import QuerySet
from kubernetes.client import Configuration
from kubernetes.config.kube_config import FileOrData, KubeConfigLoader

from paas_wl.infras.cluster.models import Cluster


class DBConfigLoader:
    """Enhanced ConfigLoader, which is loaded from **db** and supporting advanced function."""

    def __init__(self, qs: Optional[QuerySet] = None):
        """
        :param qs: A Filtered QuestSet, if not provided, use `Cluster.objects.all()` as default
        """
        self._loaded = False
        self.clusters: Dict[str, Cluster] = {}
        self.configurations: Dict[str, List[Configuration]] = defaultdict(list)

        if qs is not None and qs.model is not Cluster:
            raise ValueError("Can only be loaded from Cluster QuerySet.")
        self._qs = qs or Cluster.objects.all()  # type: QuerySet

    def _load(self):
        if self._loaded:
            return

        for cluster in self._qs.all():  # type: Cluster
            self.configurations[cluster.name] = self._build_cluster_configurations(cluster)
            self.clusters[cluster.name] = cluster

        self._loaded = True

    def _build_cluster_configurations(self, cluster: Cluster) -> List[Configuration]:
        config = {
            "certificate-authority-data": cluster.ca_data,
            "client-certificate-data": cluster.cert_data,
            "client-key-data": cluster.key_data,
        }
        ssl_ca_cert = FileOrData(config, file_key_name="certificate-authority").as_file()
        cert_file = FileOrData(config, file_key_name="client-certificate").as_file()
        key_file = FileOrData(config, file_key_name="client-key").as_file()

        configurations = []
        for api_server in cluster.api_servers.order_by("created"):
            cfg = Configuration(host=api_server.host)

            # TLS 验证主机名（注：False 值也是有效的）
            if cluster.assert_hostname is not None:
                cfg.assert_hostname = cluster.assert_hostname

            # 是否使用 ssl 证书
            if ssl_ca_cert:
                cfg.ssl_ca_cert = ssl_ca_cert
            else:
                cfg.verify_ssl = False

            # Auth type: client-side certificate
            if cert_file and key_file:
                cfg.cert_file = cert_file
                cfg.key_file = key_file

            # Auth type: Bearer token
            if cluster.token_value:
                cfg.api_key["authorization"] = f"Bearer {cluster.token_value}"

            configurations.append(cfg)

        return configurations

    def get_all_cluster_names(self) -> List[str]:
        self._load()
        return list(self.clusters.keys())

    def list_configurations_by_name(self, name: str) -> Iterable[Configuration]:
        """通过 name 加载 configuration 列表"""
        self._load()
        for config in self.configurations[name]:
            yield config


class LegacyKubeConfigLoader(KubeConfigLoader):
    """Legacy ConfigLoader, which is loaded from **file** and supporting advanced function."""

    @classmethod
    def from_file(cls, filename):
        with open(filename) as f:
            return LegacyKubeConfigLoader(
                config_dict=yaml.safe_load(f), config_base_path=os.path.abspath(os.path.dirname(filename))
            )

    def _get_tag_from_context(self, context: dict) -> str:
        """从 context 中获取 tag，不存在则取 context name"""
        try:
            return context["context"]["tag"]
        except KeyError:
            return context["name"]

    def get_all_tags(self) -> List[str]:
        all_contexts_meta = self.list_contexts()
        return list({self._get_tag_from_context(context) for context in all_contexts_meta})

    def list_configurations_by_tag(self, tag: str) -> Iterable[Configuration]:
        """通过 tag 加载 configuration 列表"""

        all_contexts_meta = self.list_contexts()
        target_context_names = [
            context["name"] for context in all_contexts_meta if self._get_tag_from_context(context) == tag
        ]

        for context_name in target_context_names:
            configuration = Configuration()
            self.set_active_context(context_name)
            self.load_and_set(configuration)
            yield configuration
