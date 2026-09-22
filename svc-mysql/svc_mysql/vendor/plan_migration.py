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
import logging
from dataclasses import dataclass

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone
from paas_service.base_vendor import get_provider_cls
from paas_service.models import Plan, ServiceInstance, ServiceInstanceConfig

from svc_mysql.vendor.models import PlanMigration, PlanMigrationStatus

logger = logging.getLogger(__name__)

PUBLIC_CREDENTIAL_KEYS = ("host", "port", "name", "user")
ENV_ORDER = {"stag": 0, "prod": 1}


@dataclass
class InstanceRef:
    instance: ServiceInstance
    app_code: str
    module: str
    environment: str


@dataclass
class CopySection:
    app_code: str
    module: str
    environment: str
    service_name: str
    source_credentials: dict
    target_credentials: dict


@dataclass
class PrepareOutcome:
    section: CopySection | None = None
    skipped: str | None = None


@dataclass
class BatchResult:
    labels: list[str]
    failures: list[str]


@dataclass
class MigrationScope:
    app_code: str
    modules: list[str] | None
    environments: list[str] | None


def resolve_target_plan(name: str) -> Plan:
    """按名称找唯一的目标 plan。重名时拒绝，避免迁错租户。"""
    from django.core.management.base import CommandError

    plans = list(Plan.objects.filter(name=name))
    if not plans:
        raise CommandError(f"找不到 plan: {name}")
    if len(plans) > 1:
        tenants = ", ".join(sorted({plan.tenant_id for plan in plans}))
        raise CommandError(f"plan 名称 {name} 对应多条记录，租户: {tenants}")
    return plans[0]


def list_bound_instances(scope: MigrationScope) -> list[InstanceRef]:
    """按应用、模块、环境找出已绑定且未删除的 MySQL 实例。

    paas_app_info 存在 JSON 文本里，不能按字段索引，管理命令里全表扫描。
    """
    from django.core.management.base import CommandError

    if not scope.app_code:
        raise CommandError("需要指定应用 ID")

    wanted_modules = set(scope.modules) if scope.modules else None
    wanted_envs = set(scope.environments) if scope.environments else None
    refs: list[InstanceRef] = []
    configs = ServiceInstanceConfig.objects.select_related("instance", "instance__plan", "instance__service").filter(
        instance__to_be_deleted=False,
        instance__plan__isnull=False,
    )
    for config in configs.iterator(chunk_size=500):
        info = _read_app_info(config)
        if info.get("app_code") != scope.app_code:
            continue
        module = info.get("module") or ""
        environment = info.get("environment") or ""
        if wanted_modules is not None and module not in wanted_modules:
            continue
        if wanted_envs is not None and environment not in wanted_envs:
            continue
        refs.append(
            InstanceRef(
                instance=config.instance,
                app_code=scope.app_code,
                module=module,
                environment=environment,
            )
        )

    refs.sort(key=lambda ref: (ref.module, ENV_ORDER.get(ref.environment, 9), ref.environment))
    _ensure_scope_covered(scope, refs)
    return refs


def prepare_migrations(
    scope: MigrationScope, target_plan: Plan, developer: str
) -> tuple[list[CopySection], list[str], list[str]]:
    """预分配目标库。目标 plan 冲突在创建任何库之前拒绝。"""
    from django.core.management.base import CommandError

    refs = list_bound_instances(scope)
    _reject_target_plan_conflicts(refs, target_plan)

    sections: list[CopySection] = []
    skipped: list[str] = []
    failures: list[str] = []
    for ref in refs:
        if ref.instance.service_id and ref.instance.service_id != target_plan.service_id:
            raise CommandError(f"{_ref_label(ref)} 所属服务与目标 plan 不一致")
        try:
            outcome = _prepare_one(ref, target_plan, developer)
        except CommandError:
            raise
        except Exception as exc:  # noqa: BLE001
            # 建库异常的消息里可能含有 SQL 和密码，只记录异常类型。
            logger.error(  # noqa: TRY400
                "prepare mysql plan migration failed: %s error=%s",
                _ref_label(ref),
                type(exc).__name__,
            )
            failures.append(_ref_label(ref))
            continue
        if outcome.skipped:
            skipped.append(outcome.skipped)
        if outcome.section:
            sections.append(outcome.section)
    return sections, skipped, failures


def switch_migrations(scope: MigrationScope) -> BatchResult:
    """把 prepared 记录的目标凭证写回原实例。"""
    from django.core.management.base import CommandError

    records = list(_migration_queryset(scope, PlanMigrationStatus.PREPARED))
    if not records:
        raise CommandError("没有处于 prepared 的迁移记录")
    return _apply_each(records, _switch_one, "switch mysql plan migration failed: %s error=%s")


def revert_migrations(scope: MigrationScope) -> BatchResult:
    """把 switched 记录恢复为切换前的 plan 和凭证，状态回到 prepared。"""
    from django.core.management.base import CommandError

    records = list(_migration_queryset(scope, PlanMigrationStatus.SWITCHED))
    if not records:
        raise CommandError("没有处于 switched 的迁移记录")
    return _apply_each(records, _revert_one, "revert mysql plan migration failed: %s error=%s")


def query_migrations(scope: MigrationScope) -> list[PlanMigration]:
    return list(_migration_queryset(scope, status=None))


def render_copy_blocks(sections: list[CopySection], developer: str) -> str:
    """生成给运维复制的纯文本。不含密码。"""
    grouped: dict[tuple[str, str], list[CopySection]] = {}
    for section in sections:
        grouped.setdefault((section.app_code, section.module), []).append(section)

    blocks: list[str] = []
    for (app_code, module), items in grouped.items():
        by_env = {item.environment: item for item in items}
        envs = sorted(by_env, key=lambda env: (ENV_ORDER.get(env, 9), env))
        lines = [
            f"appCode: {app_code}",
            f"module: {module}",
            f"envs: {', '.join(envs)}",
            f"developer: {developer}" if developer else "developer:",
            "",
        ]
        for index, env in enumerate(envs):
            item = by_env[env]
            lines.extend(_credential_section(f"老 {env}", item.service_name, item.source_credentials))
            lines.append("")
            lines.extend(_credential_section(f"新 {env}", item.service_name, item.target_credentials))
            if index != len(envs) - 1:
                lines.append("")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n"


def render_status(records: list[PlanMigration]) -> str:
    if not records:
        return "没有迁移记录\n"

    blocks: list[str] = []
    for record in records:
        source = _load_credentials(record.source_credentials)
        target = _load_credentials(record.target_credentials)
        lines = [
            f"app_code: {record.app_code}",
            f"module: {record.module}",
            f"environment: {record.environment}",
            f"instance: {record.instance_id}",
            f"source_plan: {record.source_plan.name}",
            f"target_plan: {record.target_plan.name}",
            f"status: {record.status}",
            f"prepared_at: {_format_time(record.created)}",
            f"switched_at: {_format_time(record.switched_at)}",
            f"source: {source.get('host')} / {source.get('name')}",
            f"target: {target.get('host')} / {target.get('name')}",
        ]
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n"


def _apply_each(records: list[PlanMigration], action, failure_log: str) -> BatchResult:
    labels: list[str] = []
    failures: list[str] = []
    for record in records:
        label = _record_label(record)
        try:
            action(record)
        except Exception as exc:  # noqa: BLE001
            # 切换异常的消息里可能含有凭证，只记录异常类型。
            logger.error(failure_log, label, type(exc).__name__)  # noqa: TRY400
            failures.append(label)
            continue
        labels.append(label)
    return BatchResult(labels=labels, failures=failures)


def _prepare_one(ref: InstanceRef, target_plan: Plan, developer: str) -> PrepareOutcome:
    from django.core.management.base import CommandError

    with transaction.atomic():
        instance = (
            ServiceInstance.objects.select_for_update().select_related("plan", "service").get(pk=ref.instance.pk)
        )
        prepared = PlanMigration.objects.filter(instance=instance, status=PlanMigrationStatus.PREPARED).first()
        if prepared is not None:
            if prepared.target_plan_id != target_plan.pk:
                raise CommandError(
                    f"{_ref_label(ref)} 已有待切换记录，目标 plan 是 {prepared.target_plan.name}，与 {target_plan.name} 不同"
                )
            _refresh_source_snapshot(prepared, instance, developer)
            return PrepareOutcome(section=_section_from(instance, prepared))

        already_on_target = instance.plan_id == target_plan.pk
        switched_to_target = PlanMigration.objects.filter(
            instance=instance,
            status=PlanMigrationStatus.SWITCHED,
            target_plan=target_plan,
        ).exists()
        if already_on_target or switched_to_target:
            return PrepareOutcome(skipped=f"{_ref_label(ref)} 已在目标 plan {target_plan.name}，跳过")

        instance_data = _create_target_database(instance, target_plan, ref)
        record = PlanMigration.objects.create(
            instance=instance,
            app_code=ref.app_code,
            module=ref.module,
            environment=ref.environment,
            developer=developer,
            source_plan=instance.plan,
            target_plan=target_plan,
            source_credentials=json.dumps(instance.get_credentials()),
            target_credentials=json.dumps(instance_data.credentials),
            source_config=_as_config(instance.config),
            target_config=_as_config(instance_data.config),
            status=PlanMigrationStatus.PREPARED,
            tenant_id=instance.tenant_id,
        )
        logger.info(
            "prepared mysql plan migration for %s instance=%s target_plan=%s",
            _ref_label(ref),
            instance.uuid,
            target_plan.name,
        )
        return PrepareOutcome(section=_section_from(instance, record))


def _switch_one(record: PlanMigration) -> None:
    with transaction.atomic():
        instance = (
            ServiceInstance.objects.select_for_update().select_related("plan", "service").get(pk=record.instance_id)
        )
        locked = PlanMigration.objects.select_for_update().get(pk=record.pk)
        if locked.status != PlanMigrationStatus.PREPARED:
            return
        _refresh_source_snapshot(locked, instance, locked.developer)
        target_credentials = _load_credentials(locked.target_credentials)
        instance.credentials = json.dumps(target_credentials)
        instance.plan = locked.target_plan
        instance.config = {**_as_config(instance.config), **_as_config(locked.target_config)}
        instance.save(update_fields=["credentials", "plan", "config", "updated"])
        locked.status = PlanMigrationStatus.SWITCHED
        locked.switched_at = timezone.now()
        locked.save(
            update_fields=["status", "switched_at", "source_plan", "source_credentials", "source_config", "updated"]
        )
        logger.info("switched mysql plan migration for %s instance=%s", _record_label(locked), instance.uuid)


def _revert_one(record: PlanMigration) -> None:
    with transaction.atomic():
        instance = ServiceInstance.objects.select_for_update().get(pk=record.instance_id)
        locked = PlanMigration.objects.select_for_update().select_related("source_plan").get(pk=record.pk)
        if locked.status != PlanMigrationStatus.SWITCHED:
            return
        instance.credentials = locked.source_credentials
        instance.plan = locked.source_plan
        instance.config = _as_config(locked.source_config)
        instance.save(update_fields=["credentials", "plan", "config", "updated"])
        locked.status = PlanMigrationStatus.PREPARED
        locked.switched_at = None
        locked.save(update_fields=["status", "switched_at", "updated"])
        logger.info("reverted mysql plan migration for %s instance=%s", _record_label(locked), instance.uuid)


def _create_target_database(instance: ServiceInstance, target_plan: Plan, ref: InstanceRef):
    provider_cls = get_provider_cls()
    provider = provider_cls(**target_plan.get_config())
    preferred_name = f"{ref.app_code}-{ref.module}-{ref.environment}"
    return provider.create(params={"engine_app_name": preferred_name})


def _refresh_source_snapshot(record: PlanMigration, instance: ServiceInstance, developer: str) -> None:
    record.developer = developer
    record.source_plan = instance.plan
    record.source_credentials = json.dumps(instance.get_credentials())
    record.source_config = _as_config(instance.config)
    record.save(update_fields=["developer", "source_plan", "source_credentials", "source_config", "updated"])


def _section_from(instance: ServiceInstance, record: PlanMigration) -> CopySection:
    service_name = instance.service.name if instance.service_id else "mysql"
    return CopySection(
        app_code=record.app_code,
        module=record.module,
        environment=record.environment,
        service_name=service_name,
        source_credentials=instance.get_credentials(),
        target_credentials=_load_credentials(record.target_credentials),
    )


def _reject_target_plan_conflicts(refs: list[InstanceRef], target_plan: Plan) -> None:
    from django.core.management.base import CommandError

    instance_ids = [ref.instance.pk for ref in refs]
    conflicts = (
        PlanMigration.objects.filter(
            instance_id__in=instance_ids,
            status=PlanMigrationStatus.PREPARED,
        )
        .exclude(target_plan=target_plan)
        .select_related("target_plan")
    )
    conflict_by_instance = {record.instance_id: record for record in conflicts}
    messages = []
    for ref in refs:
        conflict = conflict_by_instance.get(ref.instance.pk)
        if conflict is None:
            continue
        messages.append(f"{_ref_label(ref)} 已有待切换记录，目标 plan 是 {conflict.target_plan.name}")
    if messages:
        raise CommandError("；".join(messages))


def _ensure_scope_covered(scope: MigrationScope, refs: list[InstanceRef]) -> None:
    from django.core.management.base import CommandError

    if not refs:
        raise CommandError(f"找不到应用 {scope.app_code} 在指定范围内的 MySQL 实例")
    if not scope.modules:
        return
    found = {ref.module for ref in refs}
    missing = [module for module in scope.modules if module not in found]
    if missing:
        raise CommandError(f"这些模块在指定环境没有 MySQL 实例: {', '.join(missing)}")


def _migration_queryset(scope: MigrationScope, status: str | None) -> QuerySet[PlanMigration]:
    queryset = PlanMigration.objects.select_related("source_plan", "target_plan", "instance")
    if scope.app_code:
        queryset = queryset.filter(app_code=scope.app_code)
    if scope.modules:
        queryset = queryset.filter(module__in=scope.modules)
    if scope.environments:
        queryset = queryset.filter(environment__in=scope.environments)
    if status:
        queryset = queryset.filter(status=status)
    return queryset.order_by("app_code", "module", "environment", "created")


def _credential_section(title: str, service_name: str, credentials: dict) -> list[str]:
    from django.core.management.base import CommandError

    missing = [key for key in PUBLIC_CREDENTIAL_KEYS if key not in credentials]
    if missing:
        raise CommandError(f"凭证缺少字段: {', '.join(missing)}")
    prefix = service_name.upper().replace("-", "_")
    lines = [f"{title}："]
    lines.extend(f"{prefix}_{key.upper()}: {credentials[key]}" for key in PUBLIC_CREDENTIAL_KEYS)
    return lines


def _read_app_info(config: ServiceInstanceConfig) -> dict:
    info = config.paas_app_info or {}
    if isinstance(info, str):
        return json.loads(info) if info else {}
    return info


def _load_credentials(raw: str) -> dict:
    data = json.loads(raw)
    if not isinstance(data, dict):
        return {}
    return data


def _as_config(value) -> dict:
    if not value:
        return {}
    if isinstance(value, str):
        loaded = json.loads(value)
        return loaded if isinstance(loaded, dict) else {}
    return dict(value)


def _format_time(value) -> str:
    if value is None:
        return "-"
    return timezone.localtime(value).strftime("%Y-%m-%d %H:%M:%S")


def _ref_label(ref: InstanceRef) -> str:
    return f"{ref.app_code}/{ref.module}/{ref.environment}"


def _record_label(record: PlanMigration) -> str:
    return f"{record.app_code}/{record.module}/{record.environment}"
