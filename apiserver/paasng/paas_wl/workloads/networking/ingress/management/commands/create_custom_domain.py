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

"""Command to create custom domain for application."""

from django.core.management.base import BaseCommand, CommandError

from paas_wl.workloads.networking.ingress.models import Domain
from paasng.platform.applications.models import Application


class Command(BaseCommand):
    """Create a custom domain for an application.

    This command allows creating custom domains that bypass normal validation rules,
    such as domains using the same host as the cluster's built-in domain.

    Example:
        python manage.py create_custom_domain --app_code bk_cmdb_saas --app_module web \\
            --app_env prod --domain_name subpath-dev.example.com --path_prefix /cmdb/
    """

    help = "Create a custom domain for an application"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Dry run without creating the domain")
        parser.add_argument("--app_code", type=str, required=True, help="Application code")
        parser.add_argument(
            "--app_module", type=str, help="Module name (defaults to the default module if not specified)"
        )
        parser.add_argument("--app_env", type=str, required=True, choices=["stag", "prod"], help="Environment name")
        parser.add_argument("--https_enabled", action="store_true", help="Enable HTTPS for the domain")
        parser.add_argument("--domain_name", type=str, required=True, help="Custom domain name (e.g., example.com)")
        parser.add_argument("--path_prefix", type=str, default="/", help="Path prefix (defaults to '/')")

    def handle(
        self, dry_run, app_code, app_module, app_env, https_enabled, domain_name, path_prefix, *args, **options
    ):
        # Get application, module, and environment
        try:
            application = Application.objects.get(code=app_code)
        except Application.DoesNotExist:
            raise CommandError(f"Application '{app_code}' does not exist")

        module = application.get_module(app_module)
        environment = module.envs.get(environment=app_env)

        # Normalize path prefix
        path_prefix = self._normalize_path(path_prefix)

        # Check for existing domain
        if Domain.objects.filter(
            name=domain_name,
            path_prefix=path_prefix,
            module_id=module.pk,
            environment_id=environment.pk,
            https_enabled=https_enabled,
            tenant_id=application.tenant_id,
        ).exists():
            raise CommandError(
                f"Domain '{domain_name}' with path '{path_prefix}' already exists for {module.name}/{app_env}"
            )

        # Create domain
        domain_data = {
            "name": domain_name,
            "path_prefix": path_prefix,
            "module_id": module.pk,
            "environment_id": environment.pk,
            "https_enabled": https_enabled,
            "tenant_id": application.tenant_id,
        }

        if dry_run:
            domain = Domain(**domain_data)
            self.stdout.write(self.style.WARNING("[DRY RUN] Would create custom domain:"))
        else:
            domain = Domain.objects.create(**domain_data)
            self.stdout.write(self.style.SUCCESS("Successfully created custom domain:"))

        # Print domain info
        self.stdout.write(
            f"  ID: {domain.pk or 'N/A'}\n"
            f"  URL: {domain.protocol}://{domain.name}{path_prefix}\n"
            f"  Application: {app_code}\n"
            f"  Module: {module.name}\n"
            f"  Environment: {app_env}\n"
            f"  HTTPS: {https_enabled}"
        )

    @staticmethod
    def _normalize_path(path: str) -> str:
        """Normalize path prefix to ensure it starts and ends with '/'."""
        if not path.startswith("/"):
            path = f"/{path}"
        if not path.endswith("/"):
            path = f"{path}/"
        return path
