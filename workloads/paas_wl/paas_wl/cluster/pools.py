# -*- coding: utf-8 -*-
import logging
from collections import UserDict
from typing import Dict

from blue_krill.connections.ha_endpoint_pool import HAEndpointPool
from django.conf import settings

from paas_wl.cluster.loaders import DBConfigLoader, LegacyKubeConfigLoader

logger = logging.getLogger(__name__)


class ContextConfigurationPoolMap(UserDict):
    """K8S High Performance Configuration Pool Map With Cluster Name

    The key should be cluster name, such as regionA-default, regionB-legacy
    The Value should be HAEndpointPool, which is containing EnhancedConfiguration
    """

    @classmethod
    def from_db(cls) -> Dict[str, HAEndpointPool]:
        """load ConfigurationPoolMap from db"""
        loader = DBConfigLoader()
        instance = cls()
        for cluster_name in loader.get_all_cluster_names():
            configurations = list(loader.list_configurations_by_name(cluster_name))
            if configurations:
                instance[cluster_name] = HAEndpointPool(items=configurations)
            else:
                logger.warning("Can't find any configurations for cluster %s", cluster_name)

        return instance  # type: ignore

    @classmethod
    def from_file(cls, filename=None) -> Dict[str, HAEndpointPool]:
        """[deprecated] load ConfigurationPoolMap from config file"""
        loader = LegacyKubeConfigLoader.from_file(filename or settings.KUBE_CONFIG_FILE)
        instance = cls()
        for tag in loader.get_all_tags():
            instance[tag] = HAEndpointPool(items=loader.list_configurations_by_tag(tag))

        return instance  # type: ignore
