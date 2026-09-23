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

import base64
import json
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from paas_service.base_vendor import InstanceData
from paas_service.constants import ProvisionRecordStatus
from paas_service.models import Plan, ProvisionRecord, Service, ServiceInstance, ServiceInstanceConfig
from svc_mysql.vendor.models import PlanMigration, PlanMigrationStatus

pytestmark = pytest.mark.django_db

APP_CODE = "cw-chaos"
OLD_PASSWORD = "old-secret"
NEW_PASSWORD = "new-secret"


@pytest.fixture
def service() -> Service:
    return Service.objects.create(
        name="gcs_mysql",
        category=1,
        display_name_zh_cn="MySQL",
        display_name_en="MySQL",
    )


@pytest.fixture
def source_plan(service) -> Plan:
    return Plan.objects.create(
        name="plan-a",
        service=service,
        properties={},
        config=json.dumps({"host": "10.0.0.1", "port": 3306, "user": "root", "password": "admin-a"}),
    )


@pytest.fixture
def target_plan(service) -> Plan:
    return Plan.objects.create(
        name="plan-b",
        service=service,
        properties={},
        config=json.dumps({"host": "10.0.0.2", "port": 3306, "user": "root", "password": "admin-b"}),
    )


@pytest.fixture
def other_plan(service) -> Plan:
    return Plan.objects.create(
        name="plan-c",
        service=service,
        properties={},
        config=json.dumps({"host": "10.0.0.3", "port": 3306, "user": "root", "password": "admin-c"}),
    )


def bind_instance(service, plan, module: str, environment: str, *, name: str) -> ServiceInstance:
    """创建一条已绑定到应用的 MySQL 实例。"""
    instance = ServiceInstance.objects.create(
        service=service,
        plan=plan,
        credentials=json.dumps(
            {
                "host": f"old-{environment}.db",
                "port": 10000,
                "name": name,
                "user": name,
                "password": OLD_PASSWORD,
            }
        ),
        config={"extra": "keep", "enable_tls": False},
        tenant_id=plan.tenant_id,
    )
    ServiceInstanceConfig.objects.create(
        instance=instance,
        tenant_id=instance.tenant_id,
        paas_app_info={
            "app_id": "1",
            "app_code": APP_CODE,
            "app_name": "chaos",
            "module": module,
            "environment": environment,
        },
    )
    return instance


def new_database(name: str) -> InstanceData:
    return InstanceData(
        credentials={
            "host": "new.db",
            "port": 10000,
            "name": name,
            "user": name,
            "password": NEW_PASSWORD,
        },
        config={"provider_name": "mysql", "enable_tls": True},
    )


def run_migrate(*args) -> tuple[str, str]:
    stdout, stderr = StringIO(), StringIO()
    call_command("migrate_plan", *args, stdout=stdout, stderr=stderr)
    return stdout.getvalue(), stderr.getvalue()


@pytest.fixture
def provider():
    """挡住真实建库，按调用顺序返回新库凭证。"""
    created = MagicMock()
    created.create.side_effect = [new_database("new-stag"), new_database("new-prod"), new_database("new-api")]
    provider_cls = MagicMock(return_value=created)
    with patch("svc_mysql.vendor.plan_migration.get_provider_cls", return_value=provider_cls):
        yield created


def test_prepare_keeps_instance_and_prints_copy_block(service, source_plan, target_plan, provider):
    """prepare 不改原实例，标准输出是不含密码的复制块，默认覆盖 stag 和 prod。"""
    stag = bind_instance(service, source_plan, "default", "stag", name="old-stag")
    bind_instance(service, source_plan, "default", "prod", name="old-prod")

    stdout, _stderr = run_migrate("prepare", "-a", APP_CODE, "-t", "plan-b", "-d", "contact")

    stag.refresh_from_db()
    assert stag.plan_id == source_plan.pk
    assert stag.get_credentials()["name"] == "old-stag"
    assert "appCode: cw-chaos" in stdout
    assert "envs: stag, prod" in stdout
    assert "developer: contact" in stdout
    assert "GCS_MYSQL_NAME: old-stag" in stdout
    assert "GCS_MYSQL_NAME: new-stag" in stdout
    assert "GCS_MYSQL_NAME: new-prod" in stdout
    assert OLD_PASSWORD not in stdout
    assert NEW_PASSWORD not in stdout
    assert PlanMigration.objects.filter(status=PlanMigrationStatus.PREPARED).count() == 2


def test_prepare_again_reuses_database_and_clears_omitted_developer(service, source_plan, target_plan, provider):
    """同一目标 plan 再次 prepare 不新建库；这次没传 developer 就留空。"""
    bind_instance(service, source_plan, "default", "stag", name="old-stag")
    run_migrate("prepare", "-a", APP_CODE, "-t", "plan-b", "-e", "stag", "-d", "alice")

    stdout, _stderr = run_migrate("prepare", "-a", APP_CODE, "-t", "plan-b", "-e", "stag")

    assert provider.create.call_count == 1
    assert "developer:\n" in stdout
    assert "alice" not in stdout
    assert PlanMigration.objects.get().developer == ""


def test_prepare_rejects_different_target_plan(service, source_plan, target_plan, other_plan, provider):
    """已有 prepared 且目标 plan 不同时拒绝，不再建库。"""
    bind_instance(service, source_plan, "default", "stag", name="old-stag")
    run_migrate("prepare", "-a", APP_CODE, "-t", "plan-b", "-e", "stag")

    with pytest.raises(CommandError, match="plan-b"):
        run_migrate("prepare", "-a", APP_CODE, "-t", "plan-c", "-e", "stag")

    assert provider.create.call_count == 1


def test_switch_then_revert_restores_old_credentials(service, source_plan, target_plan, provider):
    """switch 写回目标库且 uuid 不变；revert 恢复旧库，目标库记录还在。"""
    instance = bind_instance(service, source_plan, "default", "stag", name="old-stag")
    original_uuid = instance.uuid
    run_migrate("prepare", "-a", APP_CODE, "-t", "plan-b", "-e", "stag")

    run_migrate("switch", "-a", APP_CODE, "-e", "stag")

    instance.refresh_from_db()
    assert instance.uuid == original_uuid
    assert instance.plan_id == target_plan.pk
    assert instance.get_credentials()["name"] == "new-stag"
    assert PlanMigration.objects.get().status == PlanMigrationStatus.SWITCHED

    run_migrate("revert", "-a", APP_CODE, "-e", "stag")

    instance.refresh_from_db()
    record = PlanMigration.objects.get()
    assert instance.plan_id == source_plan.pk
    assert instance.get_credentials()["name"] == "old-stag"
    assert record.status == PlanMigrationStatus.PREPARED
    assert json.loads(record.target_credentials)["name"] == "new-stag"


def test_status_lists_progress_without_password(service, source_plan, target_plan, provider):
    """status 能区分中间态和已切换，并带上库名，不显示密码。"""
    bind_instance(service, source_plan, "default", "stag", name="old-stag")
    bind_instance(service, source_plan, "default", "prod", name="old-prod")
    run_migrate("prepare", "-a", APP_CODE, "-t", "plan-b")
    run_migrate("switch", "-a", APP_CODE, "-e", "prod")

    stdout, _stderr = run_migrate("status", "-a", APP_CODE)

    assert "status: prepared" in stdout
    assert "status: switched" in stdout
    assert "source: old-stag.db / old-stag" in stdout
    assert "target: new.db / new-prod" in stdout
    assert "switched_at: -" in stdout
    assert OLD_PASSWORD not in stdout
    assert NEW_PASSWORD not in stdout


def test_prepare_grants_wildcard_egress_and_copies_to_clipboard(service, source_plan, target_plan, provider):
    """新库授权 %，标准输出末尾带 OSC 52，剪贴板内容不含密码。"""
    bind_instance(service, source_plan, "default", "stag", name="old-stag")

    stdout, stderr = run_migrate("prepare", "-a", APP_CODE, "-t", "plan-b", "-e", "stag")

    egress_info = provider.create.call_args.kwargs["params"]["egress_info"]
    assert json.loads(egress_info)["egress_ips"] == ["%"]
    encoded = stdout.split("\033]52;c;", 1)[1].split("\a", 1)[0]
    clipboard = base64.b64decode(encoded).decode()
    assert "GCS_MYSQL_NAME: new-stag" in clipboard
    assert NEW_PASSWORD not in clipboard
    assert "migrate_mysql_plan" in stderr


def test_second_prepare_finishes_previous_switched_record(service, source_plan, target_plan, other_plan, provider):
    """A→B 已切换后再 prepare B→C，旧记录变为 finished，revert 不会把它切回 A。"""
    instance = bind_instance(service, source_plan, "default", "stag", name="old-stag")
    run_migrate("prepare", "-a", APP_CODE, "-t", "plan-b", "-e", "stag")
    run_migrate("switch", "-a", APP_CODE, "-e", "stag")

    run_migrate("prepare", "-a", APP_CODE, "-t", "plan-c", "-e", "stag")

    finished = PlanMigration.objects.get(source_plan=source_plan, target_plan=target_plan)
    prepared = PlanMigration.objects.get(status=PlanMigrationStatus.PREPARED)
    assert finished.status == PlanMigrationStatus.FINISHED
    assert prepared.target_plan_id == other_plan.pk

    with pytest.raises(CommandError, match="没有处于 switched"):
        run_migrate("revert", "-a", APP_CODE, "-e", "stag")

    instance.refresh_from_db()
    assert instance.plan_id == target_plan.pk
    assert instance.get_credentials()["name"] == "new-stag"


def test_revert_rejects_when_instance_left_the_target_database(service, source_plan, target_plan, provider):
    """实例已经不在记录的目标库上时，revert 不改实例。"""
    instance = bind_instance(service, source_plan, "default", "stag", name="old-stag")
    run_migrate("prepare", "-a", APP_CODE, "-t", "plan-b", "-e", "stag")
    run_migrate("switch", "-a", APP_CODE, "-e", "stag")
    credentials = instance.get_credentials()
    credentials["host"] = "moved.db"
    instance.credentials = json.dumps(credentials)
    instance.save(update_fields=["credentials"])

    with pytest.raises(CommandError, match="回切失败"):
        run_migrate("revert", "-a", APP_CODE, "-e", "stag")

    instance.refresh_from_db()
    assert instance.get_credentials()["host"] == "moved.db"
    assert PlanMigration.objects.get().status == PlanMigrationStatus.SWITCHED


def test_switch_updates_provision_record_plan(service, source_plan, target_plan, provider):
    """switch 把开通记录的 plan 一起改成目标 plan。"""
    instance = bind_instance(service, source_plan, "default", "stag", name="old-stag")
    record = ProvisionRecord.objects.create(
        provision_key="bkapp-cw-chaos-stag",
        service_instance=instance,
        plan_id=source_plan.uuid,
        status=ProvisionRecordStatus.SUCCESS,
    )
    run_migrate("prepare", "-a", APP_CODE, "-t", "plan-b", "-e", "stag")
    run_migrate("switch", "-a", APP_CODE, "-e", "stag")

    record.refresh_from_db()
    assert record.plan_id == target_plan.uuid


def test_status_lists_every_app_and_filters_by_status(service, source_plan, target_plan, provider):
    """status 不传应用时列出全部记录，并可按状态筛选。"""
    bind_instance(service, source_plan, "default", "stag", name="old-stag")
    run_migrate("prepare", "-a", APP_CODE, "-t", "plan-b", "-e", "stag")

    stdout, _stderr = run_migrate("status", "--status", "prepared")

    assert f"app_code: {APP_CODE}" in stdout
    assert "status: prepared" in stdout

    empty, _stderr = run_migrate("status", "--status", "finished")
    assert "没有迁移记录" in empty


def test_deleting_instance_keeps_migration_credentials(service, source_plan, target_plan, provider):
    """解绑实例后迁移记录还在，另一侧库的凭证没有被级联清掉。"""
    instance = bind_instance(service, source_plan, "default", "stag", name="old-stag")
    run_migrate("prepare", "-a", APP_CODE, "-t", "plan-b", "-e", "stag")

    instance.delete()

    record = PlanMigration.objects.get()
    assert record.instance_id is None
    assert json.loads(record.target_credentials)["name"] == "new-stag"
