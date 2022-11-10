# -*- coding: utf-8 -*-
from enum import Enum

from blue_krill.data_types.enum import StructuredEnum


class AppDomainSource(int, StructuredEnum):
    # "BUILT_IN" is reserved for the default ingress's domain, it looks like '{engine_app_name}.apps.com'
    BUILT_IN = 1
    # Auto-generated sub-domains
    AUTO_GEN = 2
    INDEPENDENT = 3


class AppSubpathSource(int, StructuredEnum):
    DEFAULT = 1


class DomainsStructureType(int, Enum):
    """The data structure type of given `domains`"""

    # There are 1 or many domains, all uses the default '/' as path prefix
    ALL_DIRECT_ACCESS = 1
    # There are 1 or many domains which contain multiple non-default subpaths, all domains share
    # same subpaths.
    CUSTOMIZED_SUBPATH = 2

    # A deprecated structure type, some plugins may broken when processing NON_STANDARD structure
    NON_STANDARD = -1
