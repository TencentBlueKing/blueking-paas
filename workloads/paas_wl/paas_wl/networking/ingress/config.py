# -*- coding: utf-8 -*-
import logging
from dataclasses import dataclass, field
from typing import List

from paas_wl.utils.configs import get_region_aware

logger = logging.getLogger(__name__)


@dataclass
class CustomDomainConfig:
    """Config object for application custom domain

    :param enabled: whether this module is enabled
    :param valid_domain_suffixes: if given, only allow domains ends with those suffixes
    :param allow_user_modifications: allow user modify custom domain config or not, default to True
    :param scheme: Domain name scheme
    """

    enabled: bool = False
    valid_domain_suffixes: List = field(default_factory=list)
    allow_user_modifications: bool = True


def get_custom_domain_config(region: str) -> CustomDomainConfig:
    try:
        return get_region_aware("CUSTOM_DOMAIN_CONFIG", region=region, result_cls=CustomDomainConfig)
    except KeyError:
        logger.warning("get CUSTOM_DOMAIN_CONFIG from region: %s failed, return a default value.", region)
        return CustomDomainConfig()
