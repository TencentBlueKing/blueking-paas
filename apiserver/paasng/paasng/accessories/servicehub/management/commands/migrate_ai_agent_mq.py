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

"""
将 AI Agent 应用的 RabbitMQ 绑定从旧集群迁移到新集群.

命令效果:
    1. 创建新绑定并 provision 新集群 MQ 实例.
    2. 确认新实例可用后, 删除旧的 DB 绑定记录 (远端实例保留运行, 不影响线上).
    3. 输出新旧实例 UUID 及凭证信息.

迁移后运维操作:
    1. 通知用户重新部署应用, 下次部署时新凭证会注入到 Pod 中 (新 MQ 生效)
    2. 确认新 MQ 正常工作 (检查 Pod 环境变量中 RABBITMQ_* 值是否更新)
    3. 确认无误后, 清理旧的远程实例:
       ```
       python manage.py shell -c "
       from paasng.accessories.servicehub.remote.store import get_remote_store
       from paasng.accessories.servicehub.remote.client import RemoteServiceClient
       store = get_remote_store()
       client = RemoteServiceClient(store.get_source_config('<service_uuid>'))
       client.delete_instance_synchronously('<old_instance_uuid>')
       "
       ```

使用方式:
    python manage.py migrate_ai_agent_mq \\
        --app-code <app_code> \\
        --module-name <module_name> \\
        --environment <stag|prod> \\
        [--target-plan-id <plan_uuid>]
"""

import json
import logging
import uuid

from django.core.management.base import BaseCommand, CommandError

from paasng.accessories.servicehub.binding_policy.selector import PlanSelector
from paasng.accessories.servicehub.exceptions import ServiceObjNotFound
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.models import RemoteServiceEngineAppAttachment
from paasng.platform.applications.models import Application
from paasng.platform.engine.constants import AppEnvName
from paasng.platform.modules.models import Module

logger = logging.getLogger("commands")

SERVICE_NAME = "rabbitmq"


class Command(BaseCommand):
    help = "Migrate AI Agent app single module environment MQ to new MQ cluster."

    def add_arguments(self, parser):
        parser.add_argument(
            "--app-code", dest="app_code", type=str, required=True, help="Application code, e.g. myapp"
        )
        parser.add_argument(
            "--module-name", dest="module_name", type=str, required=True, help="Module name, e.g. default"
        )
        parser.add_argument(
            "--environment",
            dest="environment",
            type=str,
            required=True,
            choices=[e.value for e in AppEnvName],
            help="Environment name, e.g. stag or prod",
        )
        parser.add_argument(
            "--target-plan-id",
            dest="target_plan_id",
            type=str,
            required=False,
            help="Optional. Explicit new plan UUID. If not provided, auto-select via binding policy.",
        )

    def handle(self, app_code: str, module_name: str, environment: str, target_plan_id: str | None, **options):  # noqa: PLR0915
        self.stdout.write(f"Starting MQ migration for {app_code}/{module_name}/{environment}")
        application, module, env, engine_app, service_obj = self._resolve_context(app_code, module_name, environment)

        # 查找现有 MQ 绑定
        old_rels = list(mixed_service_mgr.list_provisioned_rels(engine_app, service_obj))
        if not old_rels:
            self.stdout.write(
                self.style.WARNING(
                    f"[SKIPPED] No provisioned RabbitMQ binding for {app_code}/{module_name}/{environment}"
                )
            )
            return
        old_rel = old_rels[0]

        # 记录旧实例信息
        old_instance = old_rel.get_instance()
        old_plan = old_rel.get_plan()
        old_info = {
            "instance_uuid": old_instance.uuid,
            "plan_name": old_plan.name,
            "plan_uuid": old_plan.uuid,
            "credentials": old_instance.credentials_insensitive,
        }

        # 选择目标方案
        target_plan = self._resolve_target_plan(service_obj, env, target_plan_id)

        if str(old_plan.uuid) == target_plan.uuid:
            raise CommandError(
                f"The current plan ({old_plan.name}) is already the target plan; no migration is required."
            )

        self.stdout.write(f"Target plan: {target_plan.name} ({target_plan.uuid})")

        # 唯一约束 (service_id, engine_app)，必须先删旧再建新
        # delete() 后 pk=None, 失败时 save() 即可 INSERT 回滚, 无需手动维护字段列表
        old_db_obj = old_rel.db_obj
        old_db_obj.delete()
        self.stdout.write("Old binding removed, creating new binding...")

        new_attachment = None
        try:
            new_attachment = RemoteServiceEngineAppAttachment.objects.create(
                engine_app=engine_app,
                service_id=service_obj.uuid,
                plan_id=target_plan.uuid,
                credentials_enabled=old_db_obj.credentials_enabled,
                region=old_db_obj.region,
                owner=old_db_obj.owner,
                tenant_id=env.tenant_id,
            )
        except Exception as e:  # noqa: BLE001
            self._rollback_old_binding(old_db_obj)
            raise CommandError(f"Failed to create new binding: {e}")

        new_rels = list(mixed_service_mgr.list_unprovisioned_rels(engine_app, service_obj))
        if not new_rels:
            new_attachment.delete()
            self._rollback_old_binding(old_db_obj)
            raise CommandError("Failed to find newly created binding after attachment creation.")
        new_rel = new_rels[0]

        # Provision 新实例
        instance_id = None
        try:
            instance_id = self._provision_new_instance(new_rel)
        except Exception as e:  # noqa: BLE001
            new_attachment.delete()
            self._rollback_old_binding(old_db_obj)
            if instance_id:
                self._try_delete_remote_instance(new_rel, instance_id)
            raise CommandError(f"Migration failed at provisioning stage: {e}")

        # 获取新实例信息 (查询失败不影响迁移提交)
        try:
            new_instance = new_rel.get_instance()
            new_credentials = new_instance.credentials_insensitive
            instance_uuid = new_instance.uuid
        except Exception as e:  # noqa: BLE001
            self.stdout.write(
                self.style.WARNING(
                    f"Provisioning succeeded (instance_id={instance_id}), but failed to retrieve credentials: {e}"
                )
            )
            self.stdout.write(f"  [New] instance_id={instance_id}, plan={target_plan.name}")
            self.stdout.write(f"  [Old] instance={old_info['instance_uuid']}, plan={old_info['plan_name']}")
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "Migration partially completed. The new MQ instance has been created "
                    "but credential retrieval failed. Re-deploy the app and verify env vars "
                    "manually, then clean up the old instance."
                )
            )
            raise CommandError(f"Migration completed but credential retrieval failed: {e}")

        self.stdout.write(self.style.SUCCESS("Old binding removed, new binding active."))

        # 输出结果
        new_info = {
            "instance_uuid": instance_uuid,
            "plan_name": target_plan.name,
            "plan_uuid": target_plan.uuid,
            "credentials": new_credentials,
        }
        self._print_result(application.code, module.name, env.environment, old_info, new_info)

    def _resolve_context(self, app_code, module_name, environment):
        """解析并返回迁移所需的对象上下文"""
        try:
            application = Application.objects.get(code=app_code)
        except Application.DoesNotExist:
            raise CommandError(f"Application with code '{app_code}' does not exist.")
        if not application.is_ai_agent_app:
            raise CommandError(
                f"Application '{app_code}' is not an AI Agent app. This command only supports AI Agent applications."
            )

        try:
            module = application.get_module(module_name)
        except Module.DoesNotExist:
            raise CommandError(f"Module '{module_name}' does not exist in application '{app_code}'.")

        env = module.get_envs(environment=AppEnvName(environment))
        engine_app = env.get_engine_app()

        try:
            service_obj = mixed_service_mgr.find_by_name(SERVICE_NAME)
        except ServiceObjNotFound:
            raise CommandError(f"Service '{SERVICE_NAME}' not found in the platform.")

        return application, module, env, engine_app, service_obj

    def _resolve_target_plan(self, service_obj, env, target_plan_id):
        """选择目标方案, 并校验租户与绑定策略兼容性.

        若指定 --target-plan-id, 限制为只在 PlanSelector 为该环境分配的可选方案中匹配,
        并校验 plan 的 tenant_id 与 env 一致, 避免跨租户或策略外 plan.
        """
        # 先获取该环境下 binding policy 允许的全部 plan
        allowed_plans = PlanSelector().list(service_obj, env)

        if target_plan_id:
            # 从允许的 plan 中匹配, 而非从全部 active plan 中选
            target_plan = next((p for p in allowed_plans if p.uuid == target_plan_id), None)
            if target_plan is None:
                raise CommandError(
                    f"Plan '{target_plan_id}' is not in the allowed plans for this environment "
                    f"(binding policy result: {[p.name for p in allowed_plans]}). "
                    "It may belong to a different tenant or is not authorized for this env."
                )
        else:
            if not allowed_plans:
                raise CommandError("No available plan found; please specify one using --target-plan-id.")
            if len(allowed_plans) > 1:
                raise CommandError(
                    f"Multiple available plans exist: {[p.name for p in allowed_plans]}; "
                    "please specify one using --target-plan-id."
                )
            target_plan = allowed_plans[0]

        # 额外校验 tenant_id 一致 (PlanSelector 理论上已过滤, 此处作为安全兜底)
        if target_plan.tenant_id != env.tenant_id:
            raise CommandError(
                f"Plan '{target_plan.name}' tenant_id ({target_plan.tenant_id}) "
                f"does not match env tenant_id ({env.tenant_id})."
            )

        return target_plan

    def _rollback_old_binding(self, old_db_obj):
        """回滚旧绑定. 若 save 失败则输出 CRITICAL 信息供人工恢复."""
        try:
            old_db_obj.save()
            self.stdout.write("Rollback: old binding restored.")
        except Exception:
            logger.exception("CRITICAL: rollback failed, old binding lost!")
            self.stdout.write(
                self.style.ERROR(
                    "CRITICAL: Failed to restore old binding! "
                    f"Attrs: engine_app_id={old_db_obj.engine_app_id}, "
                    f"service_id={old_db_obj.service_id}, "
                    f"plan_id={old_db_obj.plan_id}, "
                    f"service_instance_id={old_db_obj.service_instance_id}, "
                    f"credentials_enabled={old_db_obj.credentials_enabled}, "
                    f"region={old_db_obj.region}, "
                    f"owner={old_db_obj.owner}, "
                    f"tenant_id={old_db_obj.tenant_id}"
                )
            )

    def _provision_new_instance(self, new_rel) -> str:
        """创建新 MQ 实例, 返回 instance_id.

        复用 RemoteEngineAppInstanceRel.provision() 的核心流程, 但始终走非幂等端点,
        避免远程因 engine_app_name 重复而拒绝不同方案的实例.
        """
        logger.info("Provisioning new instance for %s/%s", new_rel.db_engine_app.name, new_rel.get_service().name)

        params = new_rel.render_params(new_rel.remote_config.provision_params_tmpl)
        instance_id = str(uuid.uuid4())

        # 远端 POST 创建实例
        try:
            new_rel.remote_client.provision_instance(
                str(new_rel.db_obj.service_id), str(new_rel.db_obj.plan_id), instance_id, params=params
            )
        except Exception:
            logger.exception("Remote provision_instance POST failed for instance_id=%s", instance_id)
            raise

        # DB 写入
        try:
            new_rel.db_obj.service_instance_id = instance_id
            new_rel.db_obj.save(update_fields=["service_instance_id"])
        except Exception:
            logger.exception("DB save failed after successful remote provision for instance_id=%s", instance_id)
            # 远端已创建, DB 写失败 -> 尝试回收远端孤儿实例
            self._try_delete_remote_instance(new_rel, instance_id)
            raise

        # 同步实例配置 (非关键路径, 失败仅 warn)
        if new_rel.get_service().supports_inst_config():
            try:
                new_rel.sync_instance_config()
            except Exception:  # noqa: BLE001
                logger.warning("sync_instance_config failed for instance_id=%s, non-critical", instance_id)

        logger.info("Provisioned new instance %s successfully", instance_id)
        return instance_id

    def _try_delete_remote_instance(self, rel, instance_id: str):
        """尽力回收远端孤儿实例, 失败仅记录日志不影响主流程."""
        try:
            logger.warning("Attempting to clean up orphan remote instance %s", instance_id)
            rel.remote_client.delete_instance(instance_id=instance_id)
        except Exception:
            logger.exception("Failed to delete orphan remote instance %s, manual cleanup required", instance_id)

    def _print_result(self, app_code, module_name, environment, old_info, new_info):
        self.stdout.write("")
        self.stdout.write(f"  Application : {app_code}")
        self.stdout.write(f"  Module      : {module_name}")
        self.stdout.write(f"  Environment : {environment}")
        self.stdout.write("-" * 40)
        self.stdout.write("  [Old MQ]")
        self.stdout.write(f"    Plan     : {old_info['plan_name']} ({old_info['plan_uuid']})")
        self.stdout.write(f"    Instance : {old_info['instance_uuid']}")
        self.stdout.write(f"    Creds    : {json.dumps(old_info['credentials'])}")
        self.stdout.write("-" * 40)
        self.stdout.write("  [New MQ]")
        self.stdout.write(f"    Plan     : {new_info['plan_name']} ({new_info['plan_uuid']})")
        self.stdout.write(f"    Instance : {new_info['instance_uuid']}")
        self.stdout.write(f"    Creds    : {json.dumps(new_info['credentials'])}")
        self.stdout.write("-" * 40)
        self.stdout.write(self.style.SUCCESS("Migration completed successfully"))
        self.stdout.write(
            self.style.WARNING(
                "NOTE: Old MQ instance has NOT been reclaimed. "
                "Clean it up after confirming the new MQ works via redeployment."
            )
        )
