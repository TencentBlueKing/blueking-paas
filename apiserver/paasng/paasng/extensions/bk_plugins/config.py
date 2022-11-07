# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import logging
from dataclasses import dataclass

from paasng.utils.configs import get_region_aware

logger = logging.getLogger(__name__)


@dataclass
class BkPluginConfig:
    """Config object for bk plugin module

    :param allow_creation: whether an user can create an bk_plugin application
    """

    allow_creation: bool = False


def get_bk_plugin_config(region: str) -> BkPluginConfig:
    try:
        return get_region_aware("BK_PLUGIN_CONFIG", region=region, result_cls=BkPluginConfig)
    except KeyError:
        logger.warning("get BK_PLUGIN_CONFIG from region: %s failed, return a default value.", region)
        return BkPluginConfig()
