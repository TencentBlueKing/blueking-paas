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

import json
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from paas_service.base_vendor import InstanceData
from paas_service.models import Plan, Service, ServiceInstance, ServiceInstanceConfig
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
    """prepare 不改原实例，标准输出是不含密码的复制块。"""
    stag = bind_instance(service, source_plan, "default", "stag", name="old-stag")
    bind_instance(service, source_plan, "default", "prod", name="old-prod")
    original_uuid = stag.uuid

    stdout, stderr = run_migrate("prepare", "-a", APP_CODE, "-t", "plan-b", "-d", "v_jackyjxie")

    stag.refresh_from_db()
    assert stag.uuid == original_uuid
    assert stag.plan_id == source_plan.pk
    assert stag.get_credentials()["password"] == OLD_PASSWORD
    assert "appCode: cw-chaos" in stdout
    assert "module: default" in stdout
    assert "envs: stag, prod" in stdout
    assert "developer: v_jackyjxie" in stdout
    assert "老 stag：" in stdout
    assert "GCS_MYSQL_HOST: old-stag.db" in stdout
    assert "GCS_MYSQL_NAME: old-stag" in stdout
    assert "新 stag：" in stdout
    assert "GCS_MYSQL_NAME: new-stag" in stdout
    assert "新 prod：" in stdout
    assert "GCS_MYSQL_NAME: new-prod" in stdout
    assert OLD_PASSWORD not in stdout
    assert NEW_PASSWORD not in stdout
    assert "admin-b" not in stdout
    assert "预分配完成 2 条" in stderr
    assert PlanMigration.objects.filter(status=PlanMigrationStatus.PREPARED).count() == 2
    assert provider.create.call_args_list[0].kwargs["params"]["engine_app_name"] == "cw-chaos-default-stag"


def test_prepare_again_reuses_database_and_clears_omitted_developer(service, source_plan, target_plan, provider):
    """同一目标 plan 再次 prepare 不新建库；这次没传 developer 就留空。"""
    bind_instance(service, source_plan, "default", "stag", name="old-stag")
    run_migrate("prepare", "-a", APP_CODE, "-t", "plan-b", "-e", "stag", "-d", "alice")

    stdout, _stderr = run_migrate("prepare", "-a", APP_CODE, "-t", "plan-b", "-e", "stag")

    assert provider.create.call_count == 1
    assert "developer:\n" in stdout
    assert "alice" not in stdout
    assert "GCS_MYSQL_NAME: new-stag" in stdout
    record = PlanMigration.objects.get()
    assert record.developer == ""
    assert record.status == PlanMigrationStatus.PREPARED


def test_prepare_rejects_different_target_plan(service, source_plan, target_plan, other_plan, provider):
    """已有 prepared 且目标 plan 不同时，整次命令拒绝，不再建库。"""
    bind_instance(service, source_plan, "default", "stag", name="old-stag")
    run_migrate("prepare", "-a", APP_CODE, "-t", "plan-b", "-e", "stag")

    with pytest.raises(CommandError, match="plan-b"):
        run_migrate("prepare", "-a", APP_CODE, "-t", "plan-c", "-e", "stag")

    assert provider.create.call_count == 1
    assert PlanMigration.objects.get().target_plan_id == target_plan.pk


def test_prepare_skips_instance_already_switched_to_target(service, source_plan, target_plan, provider):
    """已经切到目标 plan 的实例再次 prepare 会跳过。"""
    bind_instance(service, source_plan, "default", "stag", name="old-stag")
    run_migrate("prepare", "-a", APP_CODE, "-t", "plan-b", "-e", "stag")
    run_migrate("switch", "-a", APP_CODE, "-e", "stag")

    stdout, stderr = run_migrate("prepare", "-a", APP_CODE, "-t", "plan-b", "-e", "stag")

    assert provider.create.call_count == 1
    assert stdout == ""
    assert "跳过" in stderr


def test_prepare_defaults_to_both_environments_and_respects_module(service, source_plan, target_plan, provider):
    """不传环境时 stag 和 prod 都处理；-m 只处理指定模块。"""
    bind_instance(service, source_plan, "default", "stag", name="old-stag")
    bind_instance(service, source_plan, "api", "prod", name="old-api")

    stdout, _stderr = run_migrate("prepare", "-a", APP_CODE, "-t", "plan-b", "-m", "api")

    assert "module: api" in stdout
    assert "module: default" not in stdout
    assert PlanMigration.objects.count() == 1
    assert PlanMigration.objects.get().module == "api"


def test_prepare_failure_still_prints_successful_copy_block(service, source_plan, target_plan, provider):
    """部分失败时，成功实例的复制块已经打出，且不含密码。"""
    bind_instance(service, source_plan, "default", "stag", name="old-stag")
    bind_instance(service, source_plan, "default", "prod", name="old-prod")
    provider.create.side_effect = [new_database("new-stag"), RuntimeError("boom")]
    stdout, stderr = StringIO(), StringIO()

    with pytest.raises(CommandError, match="cw-chaos/default/prod"):
        call_command(
            "migrate_plan",
            "prepare",
            "-a",
            APP_CODE,
            "-t",
            "plan-b",
            stdout=stdout,
            stderr=stderr,
        )

    text = stdout.getvalue()
    assert "GCS_MYSQL_NAME: new-stag" in text
    assert "新 prod" not in text
    assert NEW_PASSWORD not in text
    assert OLD_PASSWORD not in text
    assert "boom" not in text
    assert "boom" not in stderr.getvalue()
    assert PlanMigration.objects.filter(environment="stag").count() == 1
    assert PlanMigration.objects.filter(environment="prod").count() == 0


def test_switch_then_revert_restores_old_credentials(service, source_plan, target_plan, provider):
    """switch 写回目标库且 uuid 不变；revert 恢复旧库，目标库记录还在。"""
    instance = bind_instance(service, source_plan, "default", "stag", name="old-stag")
    original_uuid = instance.uuid
    run_migrate("prepare", "-a", APP_CODE, "-t", "plan-b", "-e", "stag")

    stdout, _stderr = run_migrate("switch", "-a", APP_CODE, "-e", "stag")

    instance.refresh_from_db()
    assert "请重新部署后使用新库" in stdout
    assert instance.uuid == original_uuid
    assert instance.plan_id == target_plan.pk
    assert instance.get_credentials()["name"] == "new-stag"
    assert instance.get_credentials()["password"] == NEW_PASSWORD
    assert instance.config["extra"] == "keep"
    assert instance.config["enable_tls"] is True
    record = PlanMigration.objects.get()
    assert record.status == PlanMigrationStatus.SWITCHED
    assert record.switched_at is not None

    stdout, _stderr = run_migrate("revert", "-a", APP_CODE, "-e", "stag")

    instance.refresh_from_db()
    record.refresh_from_db()
    assert "请重新部署后使用旧库" in stdout
    assert instance.plan_id == source_plan.pk
    assert instance.get_credentials()["name"] == "old-stag"
    assert instance.get_credentials()["password"] == OLD_PASSWORD
    assert instance.config["enable_tls"] is False
    assert record.status == PlanMigrationStatus.PREPARED
    assert record.switched_at is None
    assert json.loads(record.target_credentials)["name"] == "new-stag"


def test_status_lists_progress_without_password(service, source_plan, target_plan, provider):
    """status 能区分中间态和已切换，并带上时间和库名，不显示密码。"""
    bind_instance(service, source_plan, "default", "stag", name="old-stag")
    prod = bind_instance(service, source_plan, "default", "prod", name="old-prod")
    run_migrate("prepare", "-a", APP_CODE, "-t", "plan-b")
    run_migrate("switch", "-a", APP_CODE, "-e", "prod")

    stdout, _stderr = run_migrate("status", "-a", APP_CODE)

    assert "status: prepared" in stdout
    assert "status: switched" in stdout
    assert "source_plan: plan-a" in stdout
    assert "target_plan: plan-b" in stdout
    assert "source: old-stag.db / old-stag" in stdout
    assert "target: new.db / new-prod" in stdout
    assert f"instance: {prod.uuid}" in stdout
    assert "prepared_at: 20" in stdout
    assert "switched_at: -" in stdout
    assert "switched_at: 20" in stdout
    assert OLD_PASSWORD not in stdout
    assert NEW_PASSWORD not in stdout


def test_missing_app_is_rejected(service, source_plan, target_plan, provider):
    """范围内没有实例时直接拒绝。"""
    bind_instance(service, source_plan, "default", "stag", name="old-stag")

    with pytest.raises(CommandError, match="找不到应用"):
        run_migrate("prepare", "-a", "missing-app", "-t", "plan-b")

    assert provider.create.call_count == 0
