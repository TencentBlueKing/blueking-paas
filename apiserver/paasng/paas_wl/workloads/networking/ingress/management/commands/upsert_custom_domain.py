# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
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

"""Command to upsert custom domain for application."""

import re

from django.core.management.base import BaseCommand, CommandError

from paas_wl.workloads.networking.ingress.models import Domain
from paasng.platform.applications.models import Application, Module

DOMAIN_NAME_REGEX = re.compile(r"^[a-zA-Z0-9][-a-zA-Z0-9]{0,62}(\.[a-zA-Z0-9][-a-zA-Z0-9]{0,62})+\.?$")
PATH_PREFIX_REGEX = re.compile(r"^/([^/]+/?)*$")


class Command(BaseCommand):
    """Create or update a custom domain for an application.

    Example:
        python manage.py upsert_custom_domain --app_code bk_cmdb_saas --app_module web \
            --app_env prod --domain_name subpath-dev.example.com --path_prefix /cmdb/
    """

    help = "Create or update a custom domain for an application"

    def add_arguments(self, parser):
        parser.add_argument("--app_code", type=str, required=True, help="Application code")
        parser.add_argument("--app_module", type=str, required=True, help="Module name")
        parser.add_argument("--app_env", type=str, required=True, choices=["stag", "prod"], help="Environment name")
        parser.add_argument("--domain_name", type=str, required=True, help="Custom domain name (e.g., example.com)")
        parser.add_argument("--path_prefix", type=str, default="/", help="Path prefix (defaults to '/')")
        parser.add_argument("--https_enabled", action="store_true", help="Enable HTTPS for the domain")

    def handle(self, app_code, app_module, app_env, domain_name, path_prefix, https_enabled, *args, **options):
        # Get application, module, and environment
        try:
            application = Application.objects.get(code=app_code)
            module = application.get_module(app_module)
        except Application.DoesNotExist:
            raise CommandError(f"Application '{app_code}' does not exist")
        except Module.DoesNotExist:
            raise CommandError(f"Module '{app_module}' does not exist in application '{app_code}'")

        environment = module.envs.get(environment=app_env)

        # Validate domain data using serializer
        if not DOMAIN_NAME_REGEX.match(domain_name):
            raise CommandError(f"Validation failed: Domain name '{domain_name}' format is invalid")
        if not PATH_PREFIX_REGEX.match(path_prefix):
            raise CommandError(f"Validation failed: Path prefix '{path_prefix}' format is invalid")

        # Create or update domain using unique_together fields
        domain, created = Domain.objects.update_or_create(
            tenant_id=application.tenant_id,
            name=domain_name,
            path_prefix=path_prefix,
            module_id=module.pk,
            environment_id=environment.pk,
            defaults={"https_enabled": https_enabled},
        )

        # Print domain info
        action = "created" if created else "updated"
        self.stdout.write(self.style.SUCCESS(f"Successfully {action} custom domain:"))
        self.stdout.write(
            f"  ID: {domain.pk or 'N/A'}\n"
            f"  URL: {domain.protocol}://{domain.name}{path_prefix}\n"
            f"  Application: {app_code}\n"
            f"  Module: {module.name}\n"
            f"  Environment: {app_env}\n"
            f"  HTTPS: {https_enabled}"
        )
