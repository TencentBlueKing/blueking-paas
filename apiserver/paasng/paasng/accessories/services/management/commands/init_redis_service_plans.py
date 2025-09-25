import json
from typing import List

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from paasng.accessories.servicehub.binding_policy.manager import SvcBindingPolicyManager
from paasng.accessories.servicehub.constants import ServiceType
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.models import DefaultPolicyCreationRecord
from paasng.accessories.services.models import Plan, Service
from paasng.core.tenant.user import get_init_tenant_id


class Command(BaseCommand):
    help = "初始化本地 redis 增强服务的 Plan，在私有化版本初始化的时候执行"

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

        success_count = 0
        plans: List[str] = []
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
                plans.append(str(plan.uuid))
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

        self._init_redis_service_binding_policy(svc, plans, tenant_id)

    def _init_redis_service_binding_policy(self, svc: Service, plans: List[str], tenant_id: str):
        with transaction.atomic():
            try:
                service_obj = mixed_service_mgr.get(svc.uuid)
                SvcBindingPolicyManager(service_obj, tenant_id).set_uniform(plans=plans)
                DefaultPolicyCreationRecord.objects.update_or_create(
                    service_id=service_obj.uuid,
                    defaults={
                        "service_type": ServiceType.LOCAL,
                        "finished_at": timezone.now(),
                    },
                )
                self.stdout.write(
                    f"Set 0shared as default plan for redis service (tenant_id: {tenant_id})", self.style.SUCCESS
                )

            except Exception as e:
                self.stdout.write(f"Failed to set default plan: {str(e)}", self.style.ERROR)
