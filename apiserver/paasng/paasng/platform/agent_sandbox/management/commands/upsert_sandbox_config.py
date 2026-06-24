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

"""Command to upsert the per-app sandbox settings (resource limits, etc.)."""

from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError

from paasng.platform.agent_sandbox.constants import DEFAULT_SANDBOX_CPU, DEFAULT_SANDBOX_MEMORY
from paasng.platform.agent_sandbox.models import SandboxAppSettings
from paasng.platform.applications.models import Application


class Command(BaseCommand):
    """Create or update the per-app sandbox settings.

    Apps without settings (or with settings that leave cpu/memory unset) fall back to
    the platform default (cpu=%s core, memory=%s GB) when creating sandboxes.

    Example:
        python manage.py upsert_sandbox_config --app_code ai-agent-prod --cpu 4 --memory 2
        python manage.py upsert_sandbox_config --app_code ai-agent-prod --cpu 4
        python manage.py upsert_sandbox_config --app_code ai-agent-prod --reset
    """ % (DEFAULT_SANDBOX_CPU, DEFAULT_SANDBOX_MEMORY)

    help = "Create, update or reset the sandbox settings for an application"

    def add_arguments(self, parser):
        parser.add_argument("--app_code", type=str, required=True, help="Application code")
        parser.add_argument("--cpu", type=str, help="CPU limit in cores, e.g. 4")
        parser.add_argument("--memory", type=str, help="Memory limit in GB, e.g. 2")
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Remove the app's config so it falls back to the platform default",
        )

    def handle(self, app_code, cpu, memory, reset, *args, **options):
        try:
            application = Application.objects.get(code=app_code)
        except Application.DoesNotExist:
            raise CommandError(f"Application '{app_code}' does not exist")

        if reset:
            deleted, _ = SandboxAppSettings.objects.filter(application=application).delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Reset sandbox settings for '{app_code}' "
                    f"(removed={deleted}), now using platform default: "
                    f"cpu={DEFAULT_SANDBOX_CPU} core, memory={DEFAULT_SANDBOX_MEMORY} GB"
                )
            )
            return

        if cpu is None and memory is None:
            raise CommandError("at least one of --cpu / --memory is required unless --reset is used")

        # 只更新本次显式传入的字段，未传入的字段保持原值（新建时则保持为空，创建沙箱时回退默认）。
        update_fields: dict = {"tenant_id": application.tenant_id}
        if cpu is not None:
            update_fields["cpu"] = self._parse_decimal("cpu", cpu)
        if memory is not None:
            update_fields["memory"] = self._parse_decimal("memory", memory)

        config, created = SandboxAppSettings.objects.update_or_create(
            application=application,
            defaults=update_fields,
        )
        action = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} sandbox settings for '{app_code}': "
                f"cpu={config.cpu} core, memory={config.memory} GB"
            )
        )

    @staticmethod
    def _parse_decimal(field: str, raw: str) -> Decimal:
        try:
            return Decimal(raw)
        except (InvalidOperation, ValueError):
            raise CommandError(f"Invalid {field} value: {raw!r}, must be a number")
