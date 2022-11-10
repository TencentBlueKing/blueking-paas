# -*- coding: utf-8 -*-
import os
from collections import defaultdict
from typing import Dict, Iterable, List, Optional

import yaml
from django.db.models import QuerySet
from kubernetes.config.kube_config import FileOrData, KubeConfigLoader

from paas_wl.cluster.models import APIServer, Cluster, EnhancedConfiguration


class DBConfigLoader:
    """Enhanced ConfigLoader, which is loaded from **db** and supporting advanced function."""

    def __init__(self, qs: Optional[QuerySet] = None):
        """
        :param qs: A Filtered QuestSet, if not provided, use `Cluster.objects.all()` as default
        """
        self._loaded = False
        self.clusters: Dict[str, Cluster] = {}
        self.configurations: Dict[str, List[EnhancedConfiguration]] = defaultdict(list)

        if qs is not None and qs.model is not Cluster:
            raise ValueError("Can only be loaded from Cluster QuerySet.")
        self._qs = qs or Cluster.objects.all()  # type: QuerySet

    def _load(self):
        if self._loaded:
            return

        for cluster in self._qs.all():  # type: Cluster
            config = {
                "certificate-authority-data": cluster.ca_data,
                "client-certificate-data": cluster.cert_data,
                "client-key-data": cluster.key_data,
            }
            ssl_ca_cert = FileOrData(config, file_key_name=None, data_key_name="certificate-authority-data").as_file()
            cert_file = FileOrData(config, file_key_name=None, data_key_name="client-certificate-data").as_file()
            key_file = FileOrData(config, file_key_name=None, data_key_name="client-key-data").as_file()

            for api_server in cluster.api_servers.order_by("created"):  # type: APIServer
                self.configurations[cluster.name].append(
                    EnhancedConfiguration.create(
                        host=api_server.host,
                        overridden_hostname=api_server.overridden_hostname,
                        ssl_ca_cert=ssl_ca_cert,
                        cert_file=cert_file,
                        key_file=key_file,
                        token=cluster.token_value,
                    )
                )
            self.clusters[cluster.name] = cluster

        self._loaded = True

    def get_all_cluster_names(self) -> List[str]:
        self._load()
        return list(self.clusters.keys())

    def list_configurations_by_name(self, name: str) -> Iterable[EnhancedConfiguration]:
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
                config_dict=yaml.load(f), config_base_path=os.path.abspath(os.path.dirname(filename))
            )

    def _get_tag_from_context(self, context: dict) -> str:
        """从 context 中获取 tag，不存在则取 context name"""
        try:
            return context['context']['tag']
        except KeyError:
            return context['name']

    def get_all_tags(self) -> List[str]:
        all_contexts_meta = self.list_contexts()
        return list({self._get_tag_from_context(context) for context in all_contexts_meta})

    def list_configurations_by_tag(self, tag: str) -> Iterable[EnhancedConfiguration]:
        """通过 tag 加载 configuration 列表"""

        all_contexts_meta = self.list_contexts()
        target_context_names = [
            context['name'] for context in all_contexts_meta if self._get_tag_from_context(context) == tag
        ]

        for context_name in target_context_names:
            # use EnhancedKubeConfiguration instead
            configuration = EnhancedConfiguration()
            self.set_active_context(context_name)
            self.load_and_set(configuration)
            yield configuration

    def _load_cluster_info(self):
        """make force domain field available for config setting"""
        super()._load_cluster_info()
        setattr(self, 'overridden_hostname', self._cluster.safe_get('overridden-hostname'))

    def _set_config(self, client_configuration):
        """make force domain field into configuration"""
        super()._set_config(client_configuration)

        keys = ['overridden_hostname']
        for key in keys:
            setattr(client_configuration, key, getattr(self, key, None))
