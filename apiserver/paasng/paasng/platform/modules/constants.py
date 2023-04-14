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
from enum import Enum, IntEnum
from typing import List

from blue_krill.data_types.enum import EnumField, StructuredEnum


class ModuleName(str, Enum):
    DEFAULT = 'default'


class ExposedURLType(IntEnum):
    # eg: http://foo.com/region-bkapp-code-stag/
    SUBPATH = 1
    # eg: http://code.foo-apps.com/
    SUBDOMAIN = 2


class SourceOrigin(int, StructuredEnum):
    """Source origin defines the origin of module's source code"""

    AUTHORIZED_VCS = EnumField(1, 'Authorized VCS')
    BK_LESS_CODE = EnumField(2, 'BK-Lesscode')
    S_MART = EnumField(3, 'S-Mart')
    IMAGE_REGISTRY = EnumField(4, 'Image Registry')
    # 场景模板
    SCENE = EnumField(5, 'Scene')

    @classmethod
    def get_default_origins(cls) -> List['SourceOrigin']:
        return [SourceOrigin.AUTHORIZED_VCS, SourceOrigin.IMAGE_REGISTRY]


class APP_CATEGORY(str, StructuredEnum):
    """Application category, used when setting label to images"""

    NORMAL_APP = 'normal_app'
    S_MART_APP = 'smart_app'
    LEGACY_APP = 'legacy_app'


class DeployHookType(str, StructuredEnum):
    """DeployHook Type"""

    PRE_RELEASE_HOOK = EnumField("pre-release-hook", label="部署前置钩子")

    @classmethod
    def _missing_(cls, value):
        # 兼容 value = pre_release_hook 的场景
        if value == "pre_release_hook":
            return cls.PRE_RELEASE_HOOK
        return super()._missing_(value)
