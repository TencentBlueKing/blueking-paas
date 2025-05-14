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

from typing import List

from pydantic import BaseModel, Field

from paasng.utils.structure import prepare_json_field


@prepare_json_field
class HostAlias(BaseModel):
    """域名解析

    :param ip: ip 地址
    :param hostnames: 域名列表. 如 ['www.example.com', 'cc.example.com']
    """

    ip: str
    hostnames: List[str]

    def __hash__(self):
        return hash((self.ip, tuple(sorted(self.hostnames))))

    def __eq__(self, other):
        if isinstance(other, HostAlias):
            return self.ip == other.ip and sorted(self.hostnames) == sorted(other.hostnames)
        return False


class DomainResolution(BaseModel):
    """Domain resolution

    :param nameservers: 域名服务器列表. 如 ['8.8.8.8', '8.8.4.4']
    :param host_aliases: 域名解析, 效果等同于向 /etc/hosts 中添加条目
    """

    nameservers: List[str] = Field(default_factory=list)
    host_aliases: List[HostAlias] = Field(default_factory=list)
