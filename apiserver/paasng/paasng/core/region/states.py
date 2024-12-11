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

import copy
from typing import List

from django.conf import settings
from django.utils.functional import SimpleLazyObject

from paasng.core.region.models import (
    Region,
    RegionBasicInfo,
    RegionEntranceConfig,
    RegionMobileConfig,
    RegionMulModulesConfig,
    register_region,
)
from paasng.utils.basic import ChoicesEnum

# Because it's tricky to update a variable when it has become a member of an enum
# instance, so we will use a global variable to do the trick
g_choice_labels: List = []


class RegionTypeContainer(ChoicesEnum):
    _choices_labels = g_choice_labels


def load_regions_from_settings():
    """Load region configs from settings"""
    # Dynamic register every region in settings
    for _orig_cfg in settings.REGION_CONFIGS["regions"]:
        cfg = copy.deepcopy(_orig_cfg)

        # Register to global region manager
        name = cfg.pop("name")
        display_name = cfg.pop("display_name")
        basic_info = RegionBasicInfo(**cfg.pop("basic_info"))
        # 可选配置
        module_mobile_config = RegionMobileConfig(**cfg.pop("module_mobile_config", {}))

        region = Region(
            name=name,
            display_name=display_name,
            basic_info=basic_info,
            module_mobile_config=module_mobile_config,
            entrance_config=RegionEntranceConfig(**cfg.pop("entrance_config")),
            mul_modules_config=RegionMulModulesConfig(**cfg.pop("mul_modules_config")),
            enabled_feature_flags=set(cfg.pop("enabled_feature_flags", [])),
            allow_user_modify_custom_domain=cfg.pop("allow_user_modify_custom_domain", None),
            provide_env_vars_platform=cfg.pop("provide_env_vars_platform", None),
            allow_deploy_app_by_lesscode=cfg.pop("allow_deploy_app_by_lesscode", None),
        )
        register_region(region)

        # Update choice fileds
        setattr(RegionTypeContainer, name.upper(), name)
        g_choice_labels.append((name, display_name))


load_regions_from_settings()


def get_region():
    return RegionTypeContainer


RegionType = SimpleLazyObject(get_region)
