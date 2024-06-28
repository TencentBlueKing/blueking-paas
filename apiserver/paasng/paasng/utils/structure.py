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

from functools import partial
from typing import Optional, Type

import cattr
from pydantic import BaseModel


def register(pydantic_model: Optional[Type[BaseModel]] = None, *, by_alias: bool = True, exclude_none: bool = False):
    def register_core(pydantic_model: Type[BaseModel]):
        cattr.register_structure_hook(pydantic_model, lambda obj, cl: pydantic_model.parse_obj(obj))
        cattr.register_unstructure_hook(
            pydantic_model, partial(pydantic_model.dict, by_alias=by_alias, exclude_none=exclude_none)
        )
        return pydantic_model

    if pydantic_model is not None:
        return register_core(pydantic_model)
    return register_core
