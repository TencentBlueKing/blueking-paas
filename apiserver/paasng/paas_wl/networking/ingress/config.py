# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
import logging
from dataclasses import dataclass, field
from typing import List

from paasng.utils.configs import get_region_aware

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
