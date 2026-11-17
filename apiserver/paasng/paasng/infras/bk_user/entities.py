# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

from pydantic import BaseModel

from paasng.utils.structure import register


@register
class Tenant(BaseModel):
    """租户"""

    id: str
    name: str
    status: str


@register
class VirtualUser(BaseModel):
    """租户下的虚拟用户

    :param bk_username: 蓝鲸用户唯一标识（即租户用户 ID）
    :param login_name: 登录名，同一环境下各租户内同名虚拟用户的 login_name 相同，bk_username 不同
    """

    bk_username: str
    login_name: str
    display_name: str = ""
