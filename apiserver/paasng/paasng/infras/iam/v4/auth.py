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

from typing import Dict, List, Optional

from django.db.models import Q

from paasng.infras.iam.base.backends import BaseAuthBackend
from paasng.infras.iam.base.dto import ActionRequest, AuthResource
from paasng.infras.iam.v4.http import BKIAMV4BaseClient


class BKIAMV4AuthBackend(BaseAuthBackend):
    """权限中心 V4 的鉴权实现

    各方法的具体实现分属后续子需求，当前仅提供符合契约的骨架：
    鉴权判定见 `#3 鉴权判定 V4 实现`，策略下推见 `#4 列表策略下推 V4 实现`，
    申请链接见 `#7 资源回调与申请链接 V4 适配`。

    note: 租户标识逐请求传入，因此客户端按请求创建，不在实例上缓存租户上下文
    """

    def _make_client(self, tenant_id: str) -> BKIAMV4BaseClient:
        return BKIAMV4BaseClient(tenant_id)

    def resource_type_allowed(self, username: str, tenant_id: str, action_id: str, use_cache: bool = False) -> bool:
        raise NotImplementedError("V4 鉴权判定由子需求 #3 实现")

    def resource_inst_allowed(
        self,
        username: str,
        tenant_id: str,
        action_id: str,
        resources: List[AuthResource],
        use_cache: bool = False,
    ) -> bool:
        raise NotImplementedError("V4 鉴权判定由子需求 #3 实现")

    def resource_inst_multi_actions_allowed(
        self, username: str, tenant_id: str, action_ids: List[str], resources: List[AuthResource]
    ) -> Dict[str, bool]:
        raise NotImplementedError("V4 鉴权判定由子需求 #3 实现")

    def batch_resource_multi_actions_allowed(
        self, username: str, tenant_id: str, action_ids: List[str], resources: List[AuthResource]
    ) -> Dict[str, Dict[str, bool]]:
        # 实现时需经 BKIAMV4BaseClient.call_in_batches 分批，V4 批量鉴权单次上限为 20 个条目
        raise NotImplementedError("V4 批量鉴权由子需求 #3 实现")

    def build_resource_filter(
        self, username: str, tenant_id: str, action_id: str, key_mapping: Optional[Dict[str, str]] = None
    ) -> Optional[Q]:
        raise NotImplementedError("V4 策略下推由子需求 #4 实现")

    def build_apply_url(self, tenant_id: str, action_requests: List[ActionRequest]) -> str:
        raise NotImplementedError("V4 申请链接生成由子需求 #7 实现")
