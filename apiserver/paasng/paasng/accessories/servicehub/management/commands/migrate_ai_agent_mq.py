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
    1. 解绑旧的 MQ 绑定 (仅删 DB 记录, 远程实例保留运行, 不影响线上)
    2. 绑定新的目标方案并创建全新的 MQ 实例 (使用非幂等端点创建, 避免远程因 engine_app_name 重复而拒绝不同方案的实例).
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
import uuid

from django.core.management.base import BaseCommand, CommandError

from paasng.accessories.servicehub.binding_policy.selector import PlanSelector
from paasng.accessories.servicehub.exceptions import ServiceObjNotFound
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.models import RemoteServiceEngineAppAttachment
from paasng.platform.applications.models import Application
from paasng.platform.engine.constants import AppEnvName
from paasng.platform.modules.models import Module

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
            help="Optional. Explicit New plan UUID. If not provided, auto-select via binding policy.",
        )

    def handle(self, app_code: str, module_name: str, environment: str, target_plan_id: str | None, **options):
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
        target_plan = self._resolve_target_plan(service_obj, env, target_plan_id, old_plan)

        # 保存旧绑定数据, 供失败时回滚使用
        # 解绑旧的 MQ 实例 (仅删 DB 记录, 不回收远程资源)
        old_db_obj = old_rel.db_obj
        old_db_obj.delete()

        # 绑定新的目标方案
        RemoteServiceEngineAppAttachment.objects.create(
            engine_app=engine_app,
            service_id=service_obj.uuid,
            plan_id=target_plan.uuid,
            tenant_id=env.tenant_id,
        )
        new_rels = list(mixed_service_mgr.list_unprovisioned_rels(engine_app, service_obj))
        if not new_rels:
            raise CommandError("Failed to find newly created binding after attachment creation.")
        new_rel = new_rels[0]
        try:
            self._provision_new_instance(new_rel)
        except Exception as e:  # noqa: BLE001
            # 回滚并报错：删除失败的新绑定，恢复旧绑定
            new_rel.db_obj.delete()
            old_db_obj.save()  # delete() 后 pk=None, save() 会 INSERT 新记录
            raise CommandError(f"Migration failed at provisioning stage: {e}")

        new_instance = new_rel.get_instance()
        new_info = {
            "instance_uuid": new_instance.uuid,
            "plan_name": target_plan.name,
            "plan_uuid": target_plan.uuid,
            "credentials": new_instance.credentials_insensitive,
        }

        # 输出结果
        self.stdout.write(f"App: {application.code} | Module: {module.name} | Env: {env.environment}")
        self._print_result(old_info, new_info)

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

        # 获取 RabbitMQ 服务
        try:
            service_obj = mixed_service_mgr.find_by_name(SERVICE_NAME)
        except ServiceObjNotFound:
            raise CommandError(f"Service '{SERVICE_NAME}' not found in the platform.")

        return application, module, env, engine_app, service_obj

    def _resolve_target_plan(self, service_obj, env, target_plan_id, old_plan):
        """选择目标方案"""
        if target_plan_id:
            target_plan = next((p for p in service_obj.get_plans(is_active=True) if p.uuid == target_plan_id), None)
            if target_plan is None:
                raise CommandError(f"Plan with id '{target_plan_id}' not found or is not active")
        else:
            plans = PlanSelector().list(service_obj, env)
            if not plans:
                raise CommandError("No available plan found; please specify one using --target-plan-id.")
            if len(plans) > 1:
                raise CommandError(
                    f"Multiple available plans exist: {[p.name for p in plans]}; please specify one using --target-plan-id."
                )
            target_plan = plans[0]

        if str(old_plan.uuid) == target_plan.uuid:
            raise CommandError(
                f"The current plan ({old_plan.name}) is already the target plan; no migration is required."
            )

        return target_plan

    def _provision_new_instance(self, new_rel):
        """创建新 MQ 实例"""
        # 复用 RemoteEngineAppInstanceRel.provision() 的核心流程, 但始终走非幂等端点 (不检查 supports_idempotent_provision)
        # 避免远程因 engine_app_name 重复而拒绝不同方案的实例. 旧实例保留在远端, 不影响线上运行服务, 应用重新部署后新 MQ 生效.
        params = new_rel.render_params(new_rel.remote_config.provision_params_tmpl)
        instance_id = str(uuid.uuid4())
        new_rel.remote_client.provision_instance(
            str(new_rel.db_obj.service_id), str(new_rel.db_obj.plan_id), instance_id, params=params
        )
        new_rel.db_obj.service_instance_id = instance_id
        new_rel.db_obj.save(update_fields=["service_instance_id"])
        if new_rel.get_service().supports_inst_config():
            new_rel.sync_instance_config()

    def _print_result(self, old_info, new_info):
        self.stdout.write("")
        self.stdout.write("Old environment MQ:")
        self.stdout.write(f"  Plan:  {old_info['plan_name']} ({old_info['plan_uuid']})")
        self.stdout.write(f"  Instance: {old_info['instance_uuid']}")
        self.stdout.write(f"  Credentials: {json.dumps(old_info['credentials'])}")
        self.stdout.write("")
        self.stdout.write("New environment MQ:")
        self.stdout.write(f"  Plan:  {new_info['plan_name']} ({new_info['plan_uuid']})")
        self.stdout.write(f"  Instance: {new_info['instance_uuid']}")
        self.stdout.write(f"  Credentials: {json.dumps(new_info['credentials'])}")
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Migration completed successfully"))
        self.stdout.write(
            self.style.WARNING(
                "NOTE: Old MQ instance has NOT been reclaimed. "
                "Clean it up after confirming the new MQ works via redeployment."
            )
        )
