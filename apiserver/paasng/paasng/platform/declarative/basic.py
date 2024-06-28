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

from typing import Dict

from pydantic import BaseModel

from .constants import OMITTED_VALUE


def remove_omitted(d: Dict) -> Dict:
    """Return a new dict without omitted values removed"""
    return {key: value for key, value in d.items() if value is not OMITTED_VALUE}


class AllowOmittedModel(BaseModel):
    """Add support for OMITTED_VALUE"""

    def dict(self, *args, **kwargs) -> Dict:
        """Remove fields with omitted values"""
        return remove_omitted(super().dict(*args, **kwargs))

    class Config:
        arbitrary_types_allowed = True
