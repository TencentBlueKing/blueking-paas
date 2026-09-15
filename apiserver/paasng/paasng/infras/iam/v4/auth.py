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

import logging
from typing import Dict, Iterable, List, Optional

from django.db.models import Q

from paasng.infras.iam.base.backends import BaseAuthBackend
from paasng.infras.iam.base.dto import ActionRequest, AuthResource
from paasng.infras.iam.shim import get_paas_system_id
from paasng.infras.iam.v4.http import BKIAMV4BaseClient

logger = logging.getLogger(__name__)

# V4 的鉴权对象类型。权限中心当前只支持 user，与 V3 SDK 的 Subject("user", username) 一致
V4_SUBJECT_TYPE_USER = "user"


class BKIAMV4AuthBackend(BaseAuthBackend):
    """权限中心 V4 的鉴权实现

    鉴权经两个 HTTP 接口完成：`direct_auth` 判定单资源单操作，`direct_auth_by_actions`
    判定单资源多操作。后者单次上限为 20 个操作，超出由客户端基座自动分批。

    策略下推见 `#4 列表策略下推 V4 实现`，申请链接见 `#7 资源回调与申请链接 V4 适配`。

    note: 租户标识逐请求传入，因此客户端按请求创建，不在实例上缓存租户上下文
    """

    def _make_client(self, tenant_id: str) -> BKIAMV4BaseClient:
        return BKIAMV4BaseClient(tenant_id)

    def resource_type_allowed(self, username: str, tenant_id: str, action_id: str, use_cache: bool = False) -> bool:
        # V4 无 SDK 侧的本地缓存，use_cache 仅为保持契约签名。
        # 当前没有调用方走缓存路径，若将来启用需在此接入缓存，而非静默忽略
        return self._auth(username, tenant_id, action_id, resource=None)

    def resource_inst_allowed(
        self,
        username: str,
        tenant_id: str,
        action_id: str,
        resource: AuthResource,
        use_cache: bool = False,
    ) -> bool:
        # use_cache 的处理同 resource_type_allowed
        return self._auth(username, tenant_id, action_id, resource)

    def _auth(self, username: str, tenant_id: str, action_id: str, resource: Optional[AuthResource]) -> bool:
        """单资源单操作判定，resource 为 None 表示该操作与资源实例无关"""
        client = self._make_client(tenant_id)

        data: Dict = {"subject": self._make_subject(username), "action_id": action_id}

        # 资源无关的操作不能带 resource 字段，否则权限中心会按资源相关的语义校验
        if resource is not None:
            data["resource"] = self._make_resource(resource)

        resp = client.call(
            client.client.direct_auth,
            path_params={"system_id": self._resolve_system_id(resource)},
            data=data,
        )
        return bool((resp.get("data") or {}).get("allowed", False))

    def resource_inst_multi_actions_allowed(
        self, username: str, tenant_id: str, action_ids: List[str], resource: AuthResource
    ) -> Dict[str, bool]:
        client = self._make_client(tenant_id)

        subject = self._make_subject(username)
        resource_data = self._make_resource(resource)

        def build_data(batch: List[str]) -> Dict:
            return {"subject": subject, "action_ids": batch, "resource": resource_data}

        # 操作数超过 20 时由基座分批。鉴权是读操作，必须显式关掉写操作人 header 的注入
        responses = client.call_in_batches(
            client.client.direct_auth_by_actions,
            action_ids,
            build_data,
            path_params={"system_id": self._resolve_system_id(resource)},
            for_write=False,
        )

        return self._collect_flags(action_ids, self._merge_data(responses), "action_id", "direct_auth_by_actions")

    def build_resource_filter(
        self, username: str, tenant_id: str, action_id: str, key_mapping: Optional[Dict[str, str]] = None
    ) -> Optional[Q]:
        raise NotImplementedError("V4 策略下推由子需求 #4 实现")

    def build_apply_url(self, tenant_id: str, action_requests: List[ActionRequest]) -> str:
        raise NotImplementedError("V4 申请链接生成由子需求 #7 实现")

    @staticmethod
    def _make_subject(username: str) -> Dict[str, str]:
        return {"type": V4_SUBJECT_TYPE_USER, "id": username}

    @staticmethod
    def _resolve_system_id(resource: Optional[AuthResource]) -> str:
        """确定本次鉴权要打到哪个系统

        V4 的系统标识走 path 参数。资源实例上已带 system（由 ResourceRequest.make_resource 填入），
        优先取它；资源无关的判定没有资源可依据，只能取开发者中心自身的系统 ID。

        note: 插件中心接入 V4 时，资源无关的分支需要改为按调用方传入的系统 ID 选择
        """
        if resource is not None:
            return resource.system

        return get_paas_system_id()

    @staticmethod
    def _make_resource(resource: AuthResource) -> Dict[str, str]:
        """构造 V4 请求体中的 resource 字段

        V4 的请求体里资源实例只有 id：system 由 path 参数承载，type 由 action 隐含，
        而 AuthResource.attribute 在 V4 没有对应字段，会被丢弃（应用侧该字段恒为空）。
        """
        return {"id": resource.id}

    @staticmethod
    def _merge_data(responses: List[Dict]) -> List[Dict]:
        """合并各批次响应中的判定结果列表

        结构不符预期的响应（data 不是列表、或列表项不是对象）在此丢弃而不抛错：
        丢弃后对应条目会在 _collect_flags 里因缺项被按未授权处理并留下告警，
        与「漏返回某一条」走同一条收敛路径，不会因结构异常变成 500
        """
        entries: List[Dict] = []
        for resp in responses:
            data = resp.get("data")
            if not isinstance(data, list):
                continue

            entries.extend(entry for entry in data if isinstance(entry, dict))

        return entries

    @staticmethod
    def _collect_flags(
        requested: Iterable[str], entries: List[Dict], key_field: str, operation_name: str
    ) -> Dict[str, bool]:
        """按发出的条目逐项回填判定结果

        以请求发出的条目为准而非直接采信响应：权限中心漏返回某一条时必须按未授权处理，
        否则缺项会在调用方的 dict 取值处变成放行。
        """
        returned = {entry.get(key_field): bool(entry.get("allowed", False)) for entry in entries}

        flags = {item: returned.get(item, False) for item in requested}

        missing = [item for item in flags if item not in returned]
        if missing:
            logger.warning(
                "bkiam api %s did not return %s for %s, treated as denied", operation_name, key_field, missing
            )

        return flags
