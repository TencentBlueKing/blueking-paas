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

from pydantic import BaseModel

from paasng.utils.structure import register


@register
class DepartmentDetail(BaseModel):
    """组织架构的详情

    :param id : 部门 ID
    :param name: 部门名称
    :param parent: 该部门的父部门，为 None 时 则代表是顶级组织
    """

    id: int
    name: str
    parent: Optional[int]


@register
class LeaderDetail(BaseModel):
    """用户上级详情，目前只用到了 username 字段"""

    username: str


@register
class UserDetail(BaseModel):
    """用户详情，目前只用到了 leader 字段

    :param leader: 用户上级
    """

    leader: List[LeaderDetail]
