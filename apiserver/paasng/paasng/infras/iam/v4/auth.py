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
from typing import Dict, Iterable, List, Optional, Set

from django.db.models import Q

from paasng.infras.iam.base.backends import BaseAuthBackend
from paasng.infras.iam.base.dto import ActionRequest, AuthResource
from paasng.infras.iam.constants import ResourceType
from paasng.infras.iam.exceptions import BKIAMGatewayServiceError
from paasng.infras.iam.shim import get_paas_system_id
from paasng.infras.iam.v4.http import BKIAMV4BaseClient

logger = logging.getLogger(__name__)

# V4 的鉴权对象类型。权限中心当前只支持 user，与 V3 SDK 的 Subject("user", username) 一致
V4_SUBJECT_TYPE_USER = "user"

# 策略下推只服务应用列表。插件列表仍走 V3：插件中心有独立的客户端，且其资源实例 ID 是
# `{pd_id}:{plugin_id}` 的层级结构，而下推接口只支持顶层资源类型
V4_PUSHDOWN_RESOURCE_TYPE = ResourceType.Application

# 应用在权限中心注册的资源实例 ID 即应用 code。V4 只返回 {type, ids}，没有 V3 那种
# 「IAM 字段名」的概念，调用方传入的 key_mapping 无从对应，落库字段只能在此固定
V4_PUSHDOWN_ORM_FIELD = "code"

# 该类型的任意资源都有权限
V4_WILDCARD_RESOURCE_ID = "*"

# 畸形内容写进日志时的单条长度与总条数上限。响应体可能很大、畸形条目可能成百上千，
# 两处都不设限的话，即便聚合成一条 warning 也足以打爆日志采集
V4_MALFORMED_REPR_LIMIT = 200
V4_MALFORMED_ENTRIES_LIMIT = 20


class BKIAMV4AuthBackend(BaseAuthBackend):
    """权限中心 V4 的鉴权实现

    鉴权经两个 HTTP 接口完成：`direct_auth` 判定单资源单操作，`direct_auth_by_actions`
    判定单资源多操作。后者单次上限为 20 个操作，超出由客户端基座自动分批。

    列表场景的策略下推走 `list_authorized_resource`，见 `build_resource_filter`。
    申请链接见 `#7 资源回调与申请链接 V4 适配`。

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
        """策略下推：查询用户有权限的应用实例，翻译为列表查询的过滤条件

        :param key_mapping: 在 V4 下被忽略，原因见 `V4_PUSHDOWN_ORM_FIELD`
        """
        client = self._make_client(tenant_id)

        try:
            # 该接口按用户与操作查询，请求体不含资源实例，系统标识只能取开发者中心自身的
            resp = client.call(
                client.client.list_authorized_resource,
                path_params={"system_id": self._resolve_system_id(None)},
                data={"subject": self._make_subject(username), "action_id": action_id},
                for_write=False,
            )
        except BKIAMGatewayServiceError as e:
            # 与 V3 的 `except AuthAPIError: return None` 对齐：拿不到策略就交回 None，由调用方
            # 落到豁免过滤器分支。不上抛，否则列表页会从「少显应用」恶化成 500
            logger.warning("build resource filter for action %s failed: %s", action_id, e)
            return None

        return self._to_orm_filter(self._collect_authorized_ids(resp, action_id))

    @staticmethod
    def _collect_authorized_ids(resp: Dict, action_id: str) -> List[str]:
        """从响应中取出应用资源类型的实例 ID"""
        data = resp.get("data") or []

        # 不校验就直接迭代的话，真值标量（如 True）会抛 TypeError、字符串会被逐字符拆开，
        # 两者都绕过 build_resource_filter 的异常收敛，把列表页打成 500
        if not isinstance(data, list):
            logger.warning(
                "bkiam api list_authorized_resource returned non-list data (%s) for action %s, treated as no policy",
                type(data).__name__,
                action_id,
            )
            return []

        resource_ids: List[str] = []
        ignored_types: Set[str] = set()
        malformed: List[str] = []

        # 与契约不符的条目一律整条跳过，不猜测其语义：每一次猜都会直接变成可见范围的偏差，
        # 而少显只是体验问题、多显是越权
        for entry in data:
            if not isinstance(entry, dict):
                malformed.append(repr(entry)[:V4_MALFORMED_REPR_LIMIT])
                continue

            # 响应可能带上级资源类型的条目（语义为「这些上级资源下的任意资源都有权限」），
            # 而应用资源只有一层、不存在上级类型，出现别的类型不展开
            resource_type = entry.get("type")
            if resource_type != V4_PUSHDOWN_RESOURCE_TYPE:
                ignored_types.add(str(resource_type))
                continue

            # ids 必须是字符串数组：字符串会被 extend 逐字符展开，其中 "*" 恰好变成 ["*"]
            # 命中通配符分支、让用户看到全部应用——那是整段实现里唯一一条会放宽可见范围的路径
            ids = entry.get("ids")
            if not isinstance(ids, list) or not all(isinstance(res_id, str) for res_id in ids):
                malformed.append(repr(ids)[:V4_MALFORMED_REPR_LIMIT])
                continue

            resource_ids.extend(ids)

        # 按整次响应聚合成一条日志：契约允许响应稳定携带上级资源类型条目，
        # 逐条打会让最高频的列表页按 QPS 刷屏
        if ignored_types or malformed:
            logger.warning(
                "bkiam api list_authorized_resource returned unusable entries for action %s, "
                "ignored resource types: %s, malformed ids or entries: %s",
                action_id,
                sorted(ignored_types),
                _summarize_malformed(malformed),
            )

        return resource_ids

    @staticmethod
    def _to_orm_filter(resource_ids: List[str]) -> Optional[Q]:
        """把有权限的应用实例 ID 翻译为 Django 过滤条件"""
        # 通配符表示对任意应用都有权限，必须返回恒真且 truthy 的条件：调用方一律以
        # `if not filters` 判断有无策略，而空 Q() 是 falsy，会让「全部可见」塌缩成豁免窗口。
        # 取 ~Q(pk=None) 与 V3 SDK 的 DjangoQuerySetConverter._any 同形
        if V4_WILDCARD_RESOURCE_ID in resource_ids:
            return ~Q(pk=None)

        # 未取得可用策略时返回 None 而非恒假条件，与 V3 的 make_filter 一致，
        # 使调用方走同一个豁免过滤器分支
        if not resource_ids:
            return None

        # 多个条目、或权限中心自身都可能给出重复 ID，重复项会无谓放大 IN 子句。
        # dict.fromkeys 保序，便于比对与复现
        unique_ids = list(dict.fromkeys(resource_ids))

        # 接口无分页参数，超长列表无法靠分页规避，只能整体拼入 IN 子句，不做截断，
        # 否则会静默少显应用
        return Q(**{f"{V4_PUSHDOWN_ORM_FIELD}__in": unique_ids})

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


def _summarize_malformed(malformed: List[str]) -> str:
    """畸形内容写日志前限定条数，只保留前几条与总数"""
    if len(malformed) <= V4_MALFORMED_ENTRIES_LIMIT:
        return str(malformed)

    return f"{malformed[:V4_MALFORMED_ENTRIES_LIMIT]} ... ({len(malformed)} in total)"
