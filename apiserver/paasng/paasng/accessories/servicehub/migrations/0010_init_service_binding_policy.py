# Generated by Django 4.2.16 on 2025-03-12 07:49

import logging
from collections import defaultdict

from django.db import migrations
from django.utils import translation
from django.conf import settings

from paasng.accessories.servicehub.constants import ServiceBindingPolicyType
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.binding_policy.policy import get_service_type

logger = logging.getLogger(__name__)


def init_service_binding_policy(apps, schema_editor):
    """
    Initialize the service binding policy for all services.

    Background:
    Service binding scheme has been changed from implicit filtering to explicit
    allocation based on ServiceBindingPolicy and ServiceBindingPrecedencePolicy.

    Purpose:
    This migration reads existing plan data and creates default ServiceBindingPolicy
    model to ensure that existing services can continue to function properly.

    Special Considerations:
    - The migration will skip initialization if any binding policies already exist,
      to prevent overwriting existing configurations.
    """
    ServiceBindingPolicy = apps.get_model("servicehub", "ServiceBindingPolicy")
    ServiceBindingPrecedencePolicy = apps.get_model("servicehub", "ServiceBindingPrecedencePolicy")

    # Check if either policy already exists
    if ServiceBindingPolicy.objects.exists() or ServiceBindingPrecedencePolicy.objects.exists():
        logger.info("Service binding policy already exists, skip init")
        return

    # mixed_service_mgr.list() 会调用 django.utils.translation.get_language()
    # 虽然配置了 settings.LANGUAGE_CODE 但是必须在国际化中间件 LocaleMiddleware 调用后才会有值
    with translation.override(settings.LANGUAGE_CODE):
        for service in mixed_service_mgr.list():
            logger.info("Init service(%s) binding policy for service", service.name)

            plans = service.get_plans()
            tenant_data = defaultdict(lambda: {"plan_ids": []})
            for p in plans:
                tenant_data[p.tenant_id]["plan_ids"].append(p.uuid)

            for tenant_id, data in tenant_data.items():
                ServiceBindingPolicy.objects.update_or_create(
                    service_id=service.uuid,
                    service_type=get_service_type(service),
                    tenant_id=tenant_id,
                    defaults={"type": ServiceBindingPolicyType.STATIC.value, "data": data},
                )

            logger.info("Service(%s) binding policy init done", service.name)


class Migration(migrations.Migration):
    dependencies = [
        ('servicehub', '0009_servicebindingpolicy_tenant_id_and_more'),
    ]

    operations = [
        migrations.RunPython(init_service_binding_policy),
    ]
