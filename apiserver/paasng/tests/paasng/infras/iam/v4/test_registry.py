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

from typing import Any, Dict, List

import pytest

from paasng.infras.iam.exceptions import (
    BKIAMApiError,
    BKIAMApiHTTPError,
    BKIAMGatewayServiceError,
    InvalidIAMIdentifierError,
)
from paasng.infras.iam.v4.definitions import (
    ActionDefinition,
    ResourceTypeDefinition,
    RoleActionDefinition,
    RoleDefinition,
    SystemDefinition,
    build_paas_system_definition,
)
from paasng.infras.iam.v4.registry import BKIAMV4ModelRegistryBackend


def sample_definition(extra_actions: List[ActionDefinition] | None = None) -> SystemDefinition:
    actions = [
        ActionDefinition(id="view_basic_info", name="基础信息查看", resource_type_id="application"),
        ActionDefinition(id="edit_basic_info", name="基础信息编辑", resource_type_id="application"),
    ]
    if extra_actions:
        actions.extend(extra_actions)
    return SystemDefinition(
        id="bk_paas3",
        name="开发者中心",
        description="desc",
        clients=["bk_paas3"],
        callback_url="http://paas.example.com/backend/api/iam-provider/applications/",
        resource_types=[ResourceTypeDefinition(id="application", name="应用")],
        actions=actions,
        roles=[
            RoleDefinition(
                id="app_administrator",
                name="应用管理员",
                description="管理员描述",
                actions=[RoleActionDefinition(id="view_basic_info", resource_type_id="application")],
            )
        ],
    )


def matching_remote(definition: SystemDefinition) -> Dict[str, Any]:
    return {
        "system": definition.to_create_payload(),
        "types": [item.to_create_payload() for item in definition.resource_types],
        "actions": [item.to_create_payload() for item in definition.actions],
        "roles": [item.to_create_payload() for item in definition.roles],
    }


class FakeIAM:
    """按 Operation.name 回放远端模型，并记录写操作"""

    def __init__(
        self,
        *,
        system: Dict | None = None,
        types: List[Dict] | None = None,
        actions: List[Dict] | None = None,
        roles: List[Dict] | None = None,
        system_missing: bool = False,
        fail_create_action_ids: List[str] | None = None,
        fail_delete_ids: List[str] | None = None,
        fail_list: bool = False,
    ):
        self.system = system
        self.types = types or []
        self.actions = actions or []
        self.roles = roles or []
        self.system_missing = system_missing
        self.fail_create_action_ids = set(fail_create_action_ids or [])
        self.fail_delete_ids = set(fail_delete_ids or [])
        self.fail_list = fail_list
        self.writes: List[Dict] = []

    def call(self, operation, **kwargs):
        name = getattr(operation, "name", "")
        if name == "retrieve_system":
            if self.system_missing:
                raise BKIAMApiHTTPError("not found", status_code=404, request_id="req-404")
            return {"data": self.system, "request_id": "req-ok"}

        if name == "batch_create_action":
            action_id = kwargs["data"][0]["id"]
            if action_id in self.fail_create_action_ids:
                raise BKIAMApiError("create action failed", request_id="req-fail")

        if name in {
            "create_system",
            "update_system",
            "batch_create_resource_type",
            "update_resource_type",
            "delete_resource_type",
            "batch_create_action",
            "update_action",
            "delete_action",
            "batch_create_role",
            "update_role",
            "delete_role",
            "batch_create_role_action",
            "batch_delete_role_action",
        }:
            deleted_id = self._deleted_identifier(name, kwargs)
            if deleted_id and deleted_id in self.fail_delete_ids:
                raise BKIAMApiError("delete blocked", request_id="req-del-fail")
            self.writes.append({"name": name, **kwargs})
            return {"data": {}, "request_id": "req-ok"}

        raise AssertionError(f"unexpected call: {name}")

    @staticmethod
    def _deleted_identifier(name: str, kwargs: Dict) -> str | None:
        path_params = kwargs.get("path_params") or {}
        if name == "delete_action":
            return path_params.get("action_id")
        if name == "delete_role":
            return path_params.get("role_id")
        if name == "delete_resource_type":
            return path_params.get("resource_type_id")
        if name == "batch_delete_role_action":
            return (kwargs.get("params") or {}).get("ids")
        return None

    def paginate(self, operation, **kwargs):
        if self.fail_list:
            raise BKIAMGatewayServiceError("list failed")
        name = getattr(operation, "name", "")
        mapping = {
            "list_resource_type": self.types,
            "list_action": self.actions,
            "list_role": self.roles,
        }
        return iter(mapping[name])


@pytest.fixture()
def backend() -> BKIAMV4ModelRegistryBackend:
    return BKIAMV4ModelRegistryBackend("tenant-foo")


def bind_fake(backend: BKIAMV4ModelRegistryBackend, fake: FakeIAM):
    setattr(backend, "call", fake.call)
    setattr(backend, "paginate", fake.paginate)


class TestIdempotentSync:
    def test_creates_all_when_remote_empty(self, backend):
        """V4 侧无模型时，本地系统/资源类型/操作/角色均应创建"""
        definition = sample_definition()
        fake = FakeIAM(system_missing=True)
        bind_fake(backend, fake)

        result = backend.sync_definition(definition)

        created_ids = {(item.kind, item.identifier) for item in result.created}
        assert created_ids == {
            ("system", "bk_paas3"),
            ("resource_type", "application"),
            ("action", "view_basic_info"),
            ("action", "edit_basic_info"),
            ("role", "app_administrator"),
        }
        assert result.counts() == {"created": 5, "updated": 0, "deleted": 0, "warnings": 0, "failures": 0}
        assert {item["name"] for item in fake.writes} == {
            "create_system",
            "batch_create_resource_type",
            "batch_create_action",
            "batch_create_role",
        }

    def test_no_write_when_already_synced(self, backend):
        definition = sample_definition()
        remote = matching_remote(definition)
        fake = FakeIAM(
            system=remote["system"], types=remote["types"], actions=remote["actions"], roles=remote["roles"]
        )
        bind_fake(backend, fake)

        result = backend.sync_definition(definition)

        assert result.counts() == {"created": 0, "updated": 0, "deleted": 0, "warnings": 0, "failures": 0}
        assert fake.writes == []

    def test_creates_only_new_action(self, backend):
        definition = sample_definition(
            extra_actions=[ActionDefinition(id="basic_develop", name="基础开发", resource_type_id="application")]
        )
        baseline = sample_definition()
        remote = matching_remote(baseline)
        fake = FakeIAM(
            system=remote["system"], types=remote["types"], actions=remote["actions"], roles=remote["roles"]
        )
        bind_fake(backend, fake)

        result = backend.sync_definition(definition)

        assert [(item.kind, item.identifier) for item in result.created] == [("action", "basic_develop")]
        assert result.updated == []
        assert [item["name"] for item in fake.writes] == ["batch_create_action"]
        assert fake.writes[0]["data"][0]["id"] == "basic_develop"

    def test_warns_and_does_not_delete_extra_action(self, backend):
        definition = sample_definition()
        remote = matching_remote(definition)
        remote["actions"].append({"id": "obsolete_action", "name": "已废弃", "resource_type_id": "application"})
        fake = FakeIAM(
            system=remote["system"], types=remote["types"], actions=remote["actions"], roles=remote["roles"]
        )
        bind_fake(backend, fake)

        result = backend.sync_definition(definition)

        assert [(item.kind, item.identifier) for item in result.warnings] == [("action", "obsolete_action")]
        assert "未执行删除" in result.warnings[0].detail
        assert all(item["name"] != "delete_action" for item in fake.writes)
        assert fake.writes == []
        assert result.deleted == []

    def test_prune_deletes_extras_in_constraint_order(self, backend):
        """prune 按解绑角色操作 → 删角色 → 删操作 → 删资源类型的顺序清理多余项

        覆盖两类解绑：现存角色多出的操作，以及废弃角色上残留的多条绑定。
        """
        definition = sample_definition()
        remote = matching_remote(definition)
        remote["types"].append({"id": "obsolete_type", "name": "废弃类型"})
        remote["actions"].append({"id": "obsolete_action", "name": "已废弃", "resource_type_id": "application"})
        remote["roles"][0]["actions"].append({"id": "obsolete_action", "resource_type_id": "application"})
        remote["roles"].append(
            {
                "id": "obsolete_role",
                "name": "废弃角色",
                "description": "",
                "actions": [
                    {"id": "obsolete_action", "resource_type_id": "application"},
                    {"id": "view_basic_info", "resource_type_id": "application"},
                ],
            }
        )
        fake = FakeIAM(
            system=remote["system"], types=remote["types"], actions=remote["actions"], roles=remote["roles"]
        )
        bind_fake(backend, fake)

        result = backend.sync_definition(definition, prune=True)

        assert [(item.kind, item.identifier) for item in result.deleted] == [
            ("role_action", "app_administrator:obsolete_action"),
            ("role_action", "obsolete_role:obsolete_action"),
            ("role_action", "obsolete_role:view_basic_info"),
            ("role", "obsolete_role"),
            ("action", "obsolete_action"),
            ("resource_type", "obsolete_type"),
        ]
        assert result.warnings == []
        assert [item["name"] for item in fake.writes] == [
            "batch_delete_role_action",
            "batch_delete_role_action",
            "batch_delete_role_action",
            "delete_role",
            "delete_action",
            "delete_resource_type",
        ]

    def test_prune_records_failure_and_continues(self, backend):
        definition = sample_definition()
        remote = matching_remote(definition)
        remote["actions"].append({"id": "obsolete_action", "name": "已废弃", "resource_type_id": "application"})
        remote["roles"].append({"id": "obsolete_role", "name": "废弃角色", "description": "", "actions": []})
        fake = FakeIAM(
            system=remote["system"],
            types=remote["types"],
            actions=remote["actions"],
            roles=remote["roles"],
            fail_delete_ids=["obsolete_role"],
        )
        bind_fake(backend, fake)

        result = backend.sync_definition(definition, prune=True)

        assert [(item.kind, item.identifier) for item in result.failures] == [("role", "obsolete_role")]
        assert result.failures[0].request_id == "req-del-fail"
        assert [(item.kind, item.identifier) for item in result.deleted] == [("action", "obsolete_action")]
        assert [item["name"] for item in fake.writes] == ["delete_action"]

    def test_prune_dry_run_does_not_write(self, backend):
        definition = sample_definition()
        remote = matching_remote(definition)
        remote["actions"].append({"id": "obsolete_action", "name": "已废弃", "resource_type_id": "application"})
        fake = FakeIAM(
            system=remote["system"], types=remote["types"], actions=remote["actions"], roles=remote["roles"]
        )
        bind_fake(backend, fake)

        result = backend.sync_definition(definition, dry_run=True, prune=True)

        assert [(item.kind, item.identifier) for item in result.deleted] == [("action", "obsolete_action")]
        assert result.warnings == []
        assert fake.writes == []

    def test_continues_after_single_action_failure(self, backend):
        definition = sample_definition()
        fake = FakeIAM(system_missing=True, fail_create_action_ids=["edit_basic_info"])
        bind_fake(backend, fake)

        result = backend.sync_definition(definition)

        assert ("action", "view_basic_info") in {(item.kind, item.identifier) for item in result.created}
        assert ("action", "edit_basic_info") in {(item.kind, item.identifier) for item in result.failures}
        assert result.failures[0].request_id == "req-fail"
        assert result.has_failures
        created_names = {item["name"] for item in fake.writes}
        assert "batch_create_role" in created_names

    def test_public_sync_skips_write_when_list_fails(self, backend):
        """分项同步在查询失败时不得把远端当成空列表继续创建"""
        fake = FakeIAM(fail_list=True)
        bind_fake(backend, fake)

        with pytest.raises(BKIAMApiError, match="查询现有模型失败"):
            backend.sync_actions()

        assert fake.writes == []

    def test_sync_definition_skips_children_when_list_fails(self, backend):
        definition = sample_definition()
        remote = matching_remote(definition)
        fake = FakeIAM(system=remote["system"], fail_list=True)
        bind_fake(backend, fake)

        result = backend.sync_definition(definition)

        assert result.has_failures
        assert fake.writes == []

    def test_dry_run_does_not_write(self, backend):
        definition = sample_definition()
        fake = FakeIAM(system_missing=True)
        bind_fake(backend, fake)

        result = backend.sync_definition(definition, dry_run=True)

        assert len(result.created) == 5
        assert fake.writes == []

    def test_invalid_identifier_fails_before_any_request(self, backend):
        definition = sample_definition()
        definition = SystemDefinition(
            id="BadSystem",
            name=definition.name,
            description=definition.description,
            clients=definition.clients,
            callback_url=definition.callback_url,
            resource_types=definition.resource_types,
            actions=definition.actions,
            roles=definition.roles,
        )
        fake = FakeIAM(system_missing=True)
        bind_fake(backend, fake)

        with pytest.raises(InvalidIAMIdentifierError) as exc_info:
            backend.sync_definitions([definition])

        assert "BadSystem" in exc_info.value.identifiers
        assert fake.writes == []

    def test_full_definitions_create_expected_counts(self, backend, settings):
        """空 V4 上全量同步时，新增条目数应与本地定义一致（1 系统 + 1 资源类型 + 14 操作 + 3 角色）"""
        settings.IAM_PAAS_V3_SYSTEM_ID = "bk_paas3"
        settings.IAM_APP_CODE = "bk_paas3"
        settings.BK_IAM_RESOURCE_API_HOST = "http://paas.example.com"

        fake = FakeIAM(system_missing=True)
        bind_fake(backend, fake)
        aggregated = backend.sync_definitions([build_paas_system_definition()])

        assert [result.counts()["created"] for result in aggregated.results] == [19]
        assert aggregated.created_count == 19
        assert aggregated.updated_count == 0

    def test_updates_changed_action_name(self, backend):
        definition = sample_definition()
        remote = matching_remote(definition)
        remote["actions"][0]["name"] = "旧名称"
        fake = FakeIAM(
            system=remote["system"], types=remote["types"], actions=remote["actions"], roles=remote["roles"]
        )
        bind_fake(backend, fake)

        result = backend.sync_definition(definition)

        assert [(item.kind, item.identifier) for item in result.updated] == [("action", "view_basic_info")]
        assert fake.writes[0]["name"] == "update_action"

    def test_fails_when_action_resource_type_id_drifts(self, backend):
        """resource_type_id 创建后不可变，同 ID 同名但授权维度不一致时不得当成功、不得走 update"""
        definition = sample_definition()
        remote = matching_remote(definition)
        remote["actions"][0]["resource_type_id"] = "wrong_type"
        fake = FakeIAM(
            system=remote["system"], types=remote["types"], actions=remote["actions"], roles=remote["roles"]
        )
        bind_fake(backend, fake)

        result = backend.sync_definition(definition)

        assert [(item.kind, item.identifier) for item in result.failures] == [("action", "view_basic_info")]
        assert "resource_type_id" in result.failures[0].detail
        assert "wrong_type" in result.failures[0].detail
        assert result.updated == []
        assert fake.writes == []

    def test_updates_changed_role_meta(self, backend):
        definition = sample_definition()
        remote = matching_remote(definition)
        remote["roles"][0]["name"] = "旧角色名"
        fake = FakeIAM(
            system=remote["system"], types=remote["types"], actions=remote["actions"], roles=remote["roles"]
        )
        bind_fake(backend, fake)

        result = backend.sync_definition(definition)

        assert [(item.kind, item.identifier) for item in result.updated] == [("role", "app_administrator")]
        assert [item["name"] for item in fake.writes] == ["update_role"]
        assert fake.writes[0]["data"]["name"] == "应用管理员"

    def test_adds_missing_role_actions(self, backend):
        """角色元信息一致但缺操作时，补齐操作并记一条 updated"""
        definition = sample_definition()
        remote = matching_remote(definition)
        remote["roles"][0]["actions"] = []
        fake = FakeIAM(
            system=remote["system"], types=remote["types"], actions=remote["actions"], roles=remote["roles"]
        )
        bind_fake(backend, fake)

        result = backend.sync_definition(definition)

        assert [(item.kind, item.identifier) for item in result.updated] == [("role", "app_administrator")]
        assert result.updated[0].detail == "补充角色操作: view_basic_info"
        assert [item["name"] for item in fake.writes] == ["batch_create_role_action"]
        assert fake.writes[0]["data"] == [{"id": "view_basic_info", "resource_type_id": "application"}]

    def test_role_meta_and_actions_change_recorded_once(self, backend):
        """元信息与操作同时变更时发两次写，但同一角色只记一条 updated"""
        definition = sample_definition()
        remote = matching_remote(definition)
        remote["roles"][0]["name"] = "旧角色名"
        remote["roles"][0]["actions"] = []
        fake = FakeIAM(
            system=remote["system"], types=remote["types"], actions=remote["actions"], roles=remote["roles"]
        )
        bind_fake(backend, fake)

        result = backend.sync_definition(definition)

        assert [(item.kind, item.identifier) for item in result.updated] == [("role", "app_administrator")]
        assert [item["name"] for item in fake.writes] == ["update_role", "batch_create_role_action"]
