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
from typing import Any, Optional

from pydantic import BaseModel, validator


class AbortedDetailsPolicy(BaseModel):
    """`policy` field of `AbortedDetails`"""

    reason: str
    name: str
    is_interrupted: bool = False


class AbortedDetails(BaseModel):
    """A model for storing aborted details, such as "reason" and other infos

    :param extra_data: reserved field for storing extra info
    """

    aborted: bool
    policy: Optional[AbortedDetailsPolicy]
    extra_data: Optional[Any]

    @validator("policy", always=True)
    def data_not_empty(cls, v, values, **kwargs):
        if values.get("aborted") and v is None:
            raise ValueError('"data" can not be empty when aborted is "True"!')
        return v
