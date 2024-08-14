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

from typing import List, Optional

from pydantic import BaseModel, Field

from paasng.utils.structure import prepare_json_field

from .utils import set_alias_field


@prepare_json_field
class SvcDiscEntryBkSaaS(BaseModel):
    """A service discovery entry that represents an application and an optional module."""

    bk_app_code: str
    module_name: Optional[str] = None

    def __init__(self, **data):
        # db 旧数据使用了 camel case
        data = set_alias_field(data, "bkAppCode", to="bk_app_code")
        data = set_alias_field(data, "moduleName", to="module_name")

        super().__init__(**data)

    def __hash__(self):
        return hash((self.bk_app_code, self.module_name))

    def __eq__(self, other):
        if isinstance(other, SvcDiscEntryBkSaaS):
            return self.bk_app_code == other.bk_app_code and self.module_name == other.module_name
        return False


class SvcDiscConfig(BaseModel):
    """Service discovery config"""

    bk_saas: List[SvcDiscEntryBkSaaS] = Field(default_factory=list)
