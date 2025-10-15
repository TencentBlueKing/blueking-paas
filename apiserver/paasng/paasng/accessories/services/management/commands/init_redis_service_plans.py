import json
from typing import List

from django.core.management.base import BaseCommand
from django.db import transaction

from paasng.accessories.servicehub.binding_policy.manager import SvcBindingPolicyManager
from paasng.accessories.servicehub.manager import mark_default_policy_creation_finished, mixed_service_mgr
from paasng.accessories.servicehub.services import ServiceObj
from paasng.accessories.services.models import Plan, Service
from paasng.core.tenant.user import get_init_tenant_id


class Command(BaseCommand):
    help = "初始化本地 redis 增强服务的 Plan，在私有化版本初始化的时候执行"

    # Note: PLAN_CONFIGS 中第一个方案是默认方案，不能轻易修改顺序
    PLAN_CONFIGS = [
        {"name": "0shared", "spec_type": "共享实例", "description": "共享实例"},
        {"name": "1exclusive", "spec_type": "独占实例", "description": "独占实例"},
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant_id",
            dest="tenant_id",
            required=False,
            default=get_init_tenant_id(),
            help="tenant id",
        )

    def handle(self, tenant_id, *args, **kwargs):
        svc = Service.objects.filter(name="redis").first()
        if not svc:
            self.stdout.write(self.style.WARNING("redis service not exists, skip init plan"))
            return

        service_obj = mixed_service_mgr.get(svc.uuid)
        success_count = 0
        plan_uuids: List[str] = []
        try:
            for config in self.PLAN_CONFIGS:
                plan, created = Plan.objects.get_or_create(
                    service=svc,
                    name=config["name"],
                    tenant_id=tenant_id,
                    defaults={
                        "config": json.dumps({"specifications": {"type": config["spec_type"]}}),
                        "is_active": True,
                        "description": config["description"],
                    },
                )
                plan_uuids.append(str(plan.uuid))
                if created:
                    self.stdout.write(
                        f'Init  Plan: {config["name"]} ({config["spec_type"]}) success', self.style.SUCCESS
                    )
                    success_count += 1
                else:
                    self.stdout.write(f'Plan already exists: {config["name"]}', self.style.NOTICE)

            msg = f"Init {success_count}/{len(self.PLAN_CONFIGS)} plans for redis service (tenant_id: {tenant_id})"
            self.stdout.write(self.style.SUCCESS(msg))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Init plans for redis service failed: {str(e)}"))

        self._init_redis_service_binding_policy(service_obj, plan_uuids, tenant_id)

    def _init_redis_service_binding_policy(self, service_obj: ServiceObj, plan_uuids: List[str], tenant_id: str):
        with transaction.atomic():
            try:
                SvcBindingPolicyManager(service_obj, tenant_id).set_uniform(plans=plan_uuids)
                mark_default_policy_creation_finished(service_obj)

                plan_names = [config["name"] for config in self.PLAN_CONFIGS]
                default_plan_name = self.PLAN_CONFIGS[0]["name"]

                self.stdout.write(
                    f"Initialized binding policy for redis service (tenant_id: {tenant_id}): "
                    f"plans=[{', '.join(plan_names)}], default_plan='{default_plan_name}'",
                    self.style.SUCCESS,
                )

            except Exception as e:
                self.stderr.write(f"Failed to set binding policy: {str(e)}", self.style.ERROR)
                raise
