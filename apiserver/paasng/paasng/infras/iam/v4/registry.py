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

from paasng.infras.iam.base.backends import BaseModelRegistryBackend
from paasng.infras.iam.v4.http import BKIAMV4BaseClient


class BKIAMV4ModelRegistryBackend(BaseModelRegistryBackend, BKIAMV4BaseClient):
    """权限中心 V4 的模型注册实现

    V3 经 SDK 的 migration JSON 模板以 upsert 语义注册模型，V4 改为标准 REST 接口，
    需自行保证幂等（先查后建、已存在则更新）。具体实现见 `#2 权限模型 V4 注册与幂等同步`。
    """

    def sync_system(self):
        raise NotImplementedError("V4 系统定义同步由子需求 #2 实现")

    def sync_resource_types(self):
        raise NotImplementedError("V4 资源类型同步由子需求 #2 实现")

    def sync_actions(self):
        raise NotImplementedError("V4 操作定义同步由子需求 #2 实现")

    def sync_roles(self):
        raise NotImplementedError("V4 角色定义同步由子需求 #2 实现")
