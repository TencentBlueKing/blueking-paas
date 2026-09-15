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

"""权限中心 V4 的模型注册与幂等同步

查询 V4 现有模型、与本地定义比对，按差异执行新增与更新。
多余项默认只告警不删除；显式 prune 时按约束顺序尝试删除。
单个条目失败时记录后继续处理其余条目。
"""

import logging
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from attrs import define, field

from paasng.infras.iam.base.backends import BaseModelRegistryBackend
from paasng.infras.iam.exceptions import BKIAMApiError, BKIAMApiHTTPError, BKIAMGatewayServiceError
from paasng.infras.iam.v4.definitions import (
    ActionDefinition,
    ResourceTypeDefinition,
    SystemDefinition,
    build_paas_system_definition,
    validate_identifiers,
)
from paasng.infras.iam.v4.http import BKIAMV4BaseClient

logger = logging.getLogger(__name__)


@define
class SyncItem:
    """同步过程中的一条结果"""

    kind: str
    identifier: str
    system_id: str
    detail: str = ""
    request_id: Optional[str] = None


@define
class ModelSyncResult:
    """单个系统的同步统计"""

    system_id: str
    created: List[SyncItem] = field(factory=list)
    updated: List[SyncItem] = field(factory=list)
    deleted: List[SyncItem] = field(factory=list)
    warnings: List[SyncItem] = field(factory=list)
    failures: List[SyncItem] = field(factory=list)

    @property
    def has_failures(self) -> bool:
        return bool(self.failures)

    def counts(self) -> Dict[str, int]:
        return {
            "created": len(self.created),
            "updated": len(self.updated),
            "deleted": len(self.deleted),
            "warnings": len(self.warnings),
            "failures": len(self.failures),
        }


@define
class AggregatedSyncResult:
    """一次命令的汇总结果"""

    results: List[ModelSyncResult] = field(factory=list)

    @property
    def created_count(self) -> int:
        return sum(len(item.created) for item in self.results)

    @property
    def updated_count(self) -> int:
        return sum(len(item.updated) for item in self.results)

    @property
    def deleted_count(self) -> int:
        return sum(len(item.deleted) for item in self.results)

    @property
    def warning_count(self) -> int:
        return sum(len(item.warnings) for item in self.results)

    @property
    def failure_count(self) -> int:
        return sum(len(item.failures) for item in self.results)

    @property
    def has_failures(self) -> bool:
        return self.failure_count > 0

    def counts(self) -> Dict[str, int]:
        return {
            "created": self.created_count,
            "updated": self.updated_count,
            "deleted": self.deleted_count,
            "warnings": self.warning_count,
            "failures": self.failure_count,
        }


class BKIAMV4ModelRegistryBackend(BaseModelRegistryBackend, BKIAMV4BaseClient):
    """权限中心 V4 的模型注册实现

    V3 经 SDK 的 migration JSON 模板以 upsert 语义注册模型，V4 改为标准 REST 接口，
    由本实现自行保证幂等（先查后建、已存在则更新；多余项默认只告警，prune 时再删）。
    """

    def sync_definitions(
        self, definitions: Sequence[SystemDefinition], *, dry_run: bool = False, prune: bool = False
    ) -> AggregatedSyncResult:
        """同步给定系统的完整模型。标识符校验在任何写操作之前执行。"""
        validate_identifiers(definitions)
        aggregated = AggregatedSyncResult()
        for definition in definitions:
            aggregated.results.append(self.sync_definition(definition, dry_run=dry_run, prune=prune))
        return aggregated

    def sync_definition(
        self, definition: SystemDefinition, *, dry_run: bool = False, prune: bool = False
    ) -> ModelSyncResult:
        result = ModelSyncResult(system_id=definition.id)
        remote_system = self._retrieve_system(definition.id, result)
        if remote_system is None and self._has_kind_failure(result, "system"):
            return result

        system_exists = remote_system is not None
        self._sync_system(definition, remote_system, result, dry_run)
        if not system_exists and self._has_kind_failure(result, "system"):
            return result

        # 系统尚未在 V4 落地时（含 dry-run），后续类型按远端为空处理，避免 list 接口 404
        if system_exists:
            remote_types = self._list_by_id(self.client.list_resource_type, definition.id, result, "resource_type")
            remote_actions = self._list_by_id(self.client.list_action, definition.id, result, "action")
            remote_roles = self._list_by_id(self.client.list_role, definition.id, result, "role")
        else:
            remote_types, remote_actions, remote_roles = {}, {}, {}

        extra_types: List[str] = []
        extra_actions: List[str] = []
        extra_role_actions: List[Tuple[str, str]] = []
        extra_roles: List[str] = []

        if remote_types is not None:
            extra_types = self._sync_resource_types(definition, remote_types, result, dry_run)
        if remote_actions is not None:
            extra_actions = self._sync_actions(definition, remote_actions, result, dry_run)
        if remote_roles is not None:
            extra_role_actions, extra_roles = self._sync_roles(definition, remote_roles, result, dry_run)

        # 删除须按约束顺序：先解绑角色操作，再删角色，再删操作，最后删资源类型
        self._sync_extras(
            definition,
            result,
            dry_run=dry_run,
            prune=prune,
            extra_role_actions=extra_role_actions,
            extra_roles=extra_roles,
            extra_actions=extra_actions,
            extra_types=extra_types,
        )
        return result

    def sync_system(self):
        definition = build_paas_system_definition()
        result = ModelSyncResult(system_id=definition.id)
        remote = self._retrieve_system(definition.id, result)
        if remote is None and self._has_kind_failure(result, "system"):
            self._raise_if_failed(result)
        self._sync_system(definition, remote, result, dry_run=False)
        self._raise_if_failed(result)

    def sync_resource_types(self):
        definition = build_paas_system_definition()
        result = ModelSyncResult(system_id=definition.id)
        remote = self._list_by_id(self.client.list_resource_type, definition.id, result, "resource_type")
        if remote is None:
            self._raise_if_failed(result)
            return
        extra_types = self._sync_resource_types(definition, remote, result, dry_run=False)
        self._sync_extras(definition, result, dry_run=False, prune=False, extra_types=extra_types)
        self._raise_if_failed(result)

    def sync_actions(self):
        definition = build_paas_system_definition()
        result = ModelSyncResult(system_id=definition.id)
        remote = self._list_by_id(self.client.list_action, definition.id, result, "action")
        if remote is None:
            self._raise_if_failed(result)
            return
        extra_actions = self._sync_actions(definition, remote, result, dry_run=False)
        self._sync_extras(definition, result, dry_run=False, prune=False, extra_actions=extra_actions)
        self._raise_if_failed(result)

    def sync_roles(self):
        definition = build_paas_system_definition()
        result = ModelSyncResult(system_id=definition.id)
        remote = self._list_by_id(self.client.list_role, definition.id, result, "role")
        if remote is None:
            self._raise_if_failed(result)
            return
        extra_role_actions, extra_roles = self._sync_roles(definition, remote, result, dry_run=False)
        self._sync_extras(
            definition,
            result,
            dry_run=False,
            prune=False,
            extra_role_actions=extra_role_actions,
            extra_roles=extra_roles,
        )
        self._raise_if_failed(result)

    # ---------------- 各类模型同步 ----------------

    def _sync_system(
        self, definition: SystemDefinition, remote: Optional[Dict], result: ModelSyncResult, dry_run: bool
    ):
        if remote is None:
            self._try_write(
                result,
                kind="system",
                identifier=definition.id,
                system_id=definition.id,
                bucket="created",
                dry_run=dry_run,
                write_fn=lambda: self.call(
                    self.client.create_system, data=definition.to_create_payload(), for_write=True
                ),
            )
            return

        if definition.differs_from(remote):
            self._try_write(
                result,
                kind="system",
                identifier=definition.id,
                system_id=definition.id,
                bucket="updated",
                dry_run=dry_run,
                write_fn=lambda: self.call(
                    self.client.update_system,
                    path_params={"system_id": definition.id},
                    data=definition.to_update_payload(),
                    for_write=True,
                ),
            )

    def _sync_resource_types(
        self, definition: SystemDefinition, remote_map: Dict[str, Dict], result: ModelSyncResult, dry_run: bool
    ) -> List[str]:
        return self._sync_named_items(
            definition=definition,
            locals_=definition.resource_types,
            remote_map=remote_map,
            result=result,
            kind="resource_type",
            dry_run=dry_run,
            create_op=self.client.batch_create_resource_type,
            update_op=self.client.update_resource_type,
            update_path_key="resource_type_id",
        )

    def _sync_actions(
        self, definition: SystemDefinition, remote_map: Dict[str, Dict], result: ModelSyncResult, dry_run: bool
    ) -> List[str]:
        return self._sync_named_items(
            definition=definition,
            locals_=definition.actions,
            remote_map=remote_map,
            result=result,
            kind="action",
            dry_run=dry_run,
            create_op=self.client.batch_create_action,
            update_op=self.client.update_action,
            update_path_key="action_id",
        )

    def _sync_roles(
        self, definition: SystemDefinition, remote_map: Dict[str, Dict], result: ModelSyncResult, dry_run: bool
    ) -> Tuple[List[Tuple[str, str]], List[str]]:
        extra_role_actions: List[Tuple[str, str]] = []
        local_ids = {role.id for role in definition.roles}
        for role in definition.roles:
            remote = remote_map.get(role.id)
            if remote is None:
                self._try_write(
                    result,
                    kind="role",
                    identifier=role.id,
                    system_id=definition.id,
                    bucket="created",
                    dry_run=dry_run,
                    write_fn=self._create_role_writer(definition.id, role.to_create_payload()),
                )
                continue

            changed = role.meta_differs_from(remote)
            missing_actions = [
                action for action in role.actions if action.identity() not in role.remote_action_ids(remote)
            ]
            if changed:
                self._try_write(
                    result,
                    kind="role",
                    identifier=role.id,
                    system_id=definition.id,
                    bucket="updated",
                    dry_run=dry_run,
                    write_fn=self._update_role_writer(definition.id, role.id, role.to_update_payload()),
                )

            if missing_actions:
                self._try_write(
                    result,
                    kind="role",
                    identifier=role.id,
                    system_id=definition.id,
                    bucket="updated" if not changed else None,
                    dry_run=dry_run,
                    write_fn=self._add_role_actions_writer(
                        definition.id, role.id, [action.to_payload() for action in missing_actions]
                    ),
                    detail="补充角色操作: " + ",".join(action.id for action in missing_actions),
                )

            extra_actions = role.remote_action_ids(remote) - role.local_action_ids()
            extra_role_actions.extend((role.id, action_id) for action_id, _ in sorted(extra_actions))

        return extra_role_actions, sorted(set(remote_map) - local_ids)

    def _sync_named_items(
        self,
        *,
        definition: SystemDefinition,
        locals_: Sequence[ResourceTypeDefinition | ActionDefinition],
        remote_map: Dict[str, Dict],
        result: ModelSyncResult,
        kind: str,
        dry_run: bool,
        create_op,
        update_op,
        update_path_key: str,
    ) -> List[str]:
        local_ids = {item.id for item in locals_}
        for item in locals_:
            remote = remote_map.get(item.id)
            if remote is None:
                self._try_write(
                    result,
                    kind=kind,
                    identifier=item.id,
                    system_id=definition.id,
                    bucket="created",
                    dry_run=dry_run,
                    write_fn=self._batch_create_writer(create_op, definition.id, item.to_create_payload()),
                )
                continue

            if isinstance(item, ActionDefinition) and item.has_immutable_mismatch(remote):
                remote_type = remote.get("resource_type_id") or ""
                self._fail(
                    result,
                    kind=kind,
                    identifier=item.id,
                    system_id=definition.id,
                    detail=(
                        f"V4 侧操作的 resource_type_id={remote_type!r} 与本地 {item.resource_type_id!r} "
                        "不一致，且创建后不可变，需删除后重建"
                    ),
                )
                continue

            if item.differs_from(remote):
                self._try_write(
                    result,
                    kind=kind,
                    identifier=item.id,
                    system_id=definition.id,
                    bucket="updated",
                    dry_run=dry_run,
                    write_fn=self._update_item_writer(
                        update_op, definition.id, update_path_key, item.id, item.to_update_payload()
                    ),
                )

        return sorted(set(remote_map) - local_ids)

    def _sync_extras(
        self,
        definition: SystemDefinition,
        result: ModelSyncResult,
        *,
        dry_run: bool,
        prune: bool,
        extra_role_actions: Optional[List[Tuple[str, str]]] = None,
        extra_roles: Optional[List[str]] = None,
        extra_actions: Optional[List[str]] = None,
        extra_types: Optional[List[str]] = None,
    ):
        """处理 V4 侧本地已无的多余项。默认告警；prune 时按约束顺序删除。"""
        for role_id, action_id in extra_role_actions or []:
            self._reconcile_extra(
                result,
                kind="role_action",
                identifier=f"{role_id}:{action_id}",
                system_id=definition.id,
                dry_run=dry_run,
                prune=prune,
                warn_detail="V4 侧角色存在本地已无的操作，未执行删除",
                write_fn=self._delete_role_actions_writer(definition.id, role_id, [action_id]),
            )
        for extra_id in extra_roles or []:
            self._reconcile_extra(
                result,
                kind="role",
                identifier=extra_id,
                system_id=definition.id,
                dry_run=dry_run,
                prune=prune,
                warn_detail="V4 侧存在本地已无的角色，未执行删除",
                write_fn=self._delete_item_writer(self.client.delete_role, definition.id, "role_id", extra_id),
            )
        for extra_id in extra_actions or []:
            self._reconcile_extra(
                result,
                kind="action",
                identifier=extra_id,
                system_id=definition.id,
                dry_run=dry_run,
                prune=prune,
                warn_detail="V4 侧存在本地已无的操作，未执行删除",
                write_fn=self._delete_item_writer(self.client.delete_action, definition.id, "action_id", extra_id),
            )
        for extra_id in extra_types or []:
            self._reconcile_extra(
                result,
                kind="resource_type",
                identifier=extra_id,
                system_id=definition.id,
                dry_run=dry_run,
                prune=prune,
                warn_detail="V4 侧存在本地已无的资源类型，未执行删除",
                write_fn=self._delete_item_writer(
                    self.client.delete_resource_type, definition.id, "resource_type_id", extra_id
                ),
            )

    def _reconcile_extra(
        self,
        result: ModelSyncResult,
        *,
        kind: str,
        identifier: str,
        system_id: str,
        dry_run: bool,
        prune: bool,
        warn_detail: str,
        write_fn: Callable,
    ):
        if not prune:
            self._warn(result, kind=kind, identifier=identifier, system_id=system_id, detail=warn_detail)
            return
        self._try_write(
            result,
            kind=kind,
            identifier=identifier,
            system_id=system_id,
            bucket="deleted",
            dry_run=dry_run,
            write_fn=write_fn,
        )

    # ---------------- 查询与错误处理 ----------------

    def _retrieve_system(self, system_id: str, result: ModelSyncResult) -> Optional[Dict]:
        try:
            resp = self.call(self.client.retrieve_system, path_params={"system_id": system_id})
        except BKIAMApiHTTPError as exc:
            if exc.status_code == 404:
                return None
            self._record_failure(result, "system", system_id, system_id, exc)
            return None
        except (BKIAMApiError, BKIAMGatewayServiceError) as exc:
            self._record_failure(result, "system", system_id, system_id, exc)
            return None
        return resp.get("data") or {}

    def _list_by_id(self, operation, system_id: str, result: ModelSyncResult, kind: str) -> Optional[Dict[str, Dict]]:
        try:
            items = list(self.paginate(operation, path_params={"system_id": system_id}))
        except (BKIAMApiError, BKIAMApiHTTPError, BKIAMGatewayServiceError) as exc:
            self._record_failure(result, kind, "*", system_id, exc, detail="查询现有模型失败")
            return None
        return {item["id"]: item for item in items if item.get("id")}

    def _batch_create_writer(self, operation, system_id: str, payload: Dict) -> Callable:
        def _write():
            self.call(operation, path_params={"system_id": system_id}, data=[payload], for_write=True)

        return _write

    def _update_item_writer(self, operation, system_id: str, path_key: str, item_id: str, payload: Dict) -> Callable:
        def _write():
            self.call(
                operation,
                path_params={"system_id": system_id, path_key: item_id},
                data=payload,
                for_write=True,
            )

        return _write

    def _create_role_writer(self, system_id: str, payload: Dict) -> Callable:
        def _write():
            self.call(
                self.client.batch_create_role,
                path_params={"system_id": system_id},
                data=[payload],
                for_write=True,
            )

        return _write

    def _update_role_writer(self, system_id: str, role_id: str, payload: Dict) -> Callable:
        def _write():
            self.call(
                self.client.update_role,
                path_params={"system_id": system_id, "role_id": role_id},
                data=payload,
                for_write=True,
            )

        return _write

    def _add_role_actions_writer(self, system_id: str, role_id: str, payloads: List[Dict]) -> Callable:
        def _write():
            self.call(
                self.client.batch_create_role_action,
                path_params={"system_id": system_id, "role_id": role_id},
                data=payloads,
                for_write=True,
            )

        return _write

    def _delete_item_writer(self, operation, system_id: str, path_key: str, item_id: str) -> Callable:
        def _write():
            self.call(
                operation,
                path_params={"system_id": system_id, path_key: item_id},
                for_write=True,
            )

        return _write

    def _delete_role_actions_writer(self, system_id: str, role_id: str, action_ids: List[str]) -> Callable:
        def _write():
            self.call(
                self.client.batch_delete_role_action,
                path_params={"system_id": system_id, "role_id": role_id},
                params={"ids": ",".join(action_ids)},
                for_write=True,
            )

        return _write

    def _try_write(
        self,
        result: ModelSyncResult,
        *,
        kind: str,
        identifier: str,
        system_id: str,
        bucket: Optional[str],
        dry_run: bool,
        write_fn: Callable,
        detail: str = "",
    ) -> Optional[bool]:
        """执行一条写操作。dry-run 只记账；失败记入 failures 并继续。

        :param bucket: created / updated / deleted；为 None 时表示该写操作从属于已记账的更新
        :returns: True 成功，False 失败，None 表示无需单独记账的附属写操作成功
        """
        item = SyncItem(kind=kind, identifier=identifier, system_id=system_id, detail=detail)
        if dry_run:
            if bucket:
                getattr(result, bucket).append(item)
            return True if bucket else None

        try:
            write_fn()
        except (BKIAMApiError, BKIAMApiHTTPError, BKIAMGatewayServiceError) as exc:
            self._record_failure(result, kind, identifier, system_id, exc, detail=detail)
            return False

        if bucket:
            getattr(result, bucket).append(item)
            return True
        return None

    def _warn(self, result: ModelSyncResult, *, kind: str, identifier: str, system_id: str, detail: str):
        item = SyncItem(kind=kind, identifier=identifier, system_id=system_id, detail=detail)
        result.warnings.append(item)
        logger.warning("iam v4 model sync warning: system=%s %s=%s %s", system_id, kind, identifier, detail)

    def _fail(self, result: ModelSyncResult, *, kind: str, identifier: str, system_id: str, detail: str):
        result.failures.append(SyncItem(kind=kind, identifier=identifier, system_id=system_id, detail=detail))
        logger.error("iam v4 model sync failed: system=%s %s=%s detail=%s", system_id, kind, identifier, detail)

    def _record_failure(
        self,
        result: ModelSyncResult,
        kind: str,
        identifier: str,
        system_id: str,
        exc: Exception,
        detail: str = "",
    ):
        request_id = getattr(exc, "request_id", None)
        message = detail or str(exc)
        result.failures.append(
            SyncItem(
                kind=kind,
                identifier=identifier,
                system_id=system_id,
                detail=message,
                request_id=request_id,
            )
        )
        logger.error(
            "iam v4 model sync failed: system=%s %s=%s request_id=%s detail=%s",
            system_id,
            kind,
            identifier,
            request_id,
            message,
        )

    @staticmethod
    def _has_kind_failure(result: ModelSyncResult, kind: str) -> bool:
        return any(item.kind == kind for item in result.failures)

    @staticmethod
    def _raise_if_failed(result: ModelSyncResult):
        if not result.has_failures:
            return
        first = result.failures[0]
        raise BKIAMApiError(first.detail or "model sync failed", request_id=first.request_id)


def sync_iam_v4_models(
    definitions: Iterable[SystemDefinition],
    *,
    tenant_id: str,
    dry_run: bool = False,
    prune: bool = False,
    operator: Optional[str] = None,
) -> AggregatedSyncResult:
    """运维命令入口：校验标识符后按系统执行幂等同步"""
    backend = BKIAMV4ModelRegistryBackend(tenant_id, operator)
    return backend.sync_definitions(list(definitions), dry_run=dry_run, prune=prune)
