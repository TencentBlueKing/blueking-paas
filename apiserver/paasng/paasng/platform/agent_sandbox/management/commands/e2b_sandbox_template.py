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

"""Command to manage the e2b sandbox templates registered on the platform."""

from pathlib import Path

import yaml
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from rest_framework import serializers

from paasng.platform.agent_sandbox.models import E2BSandboxTemplate


class _TemplateSpecSLZ(serializers.Serializer):
    """模板声明文件中的一项。未声明的字段取默认值，即文件就是该模板的完整定义。"""

    template_id = serializers.CharField(max_length=128)
    name = serializers.CharField(max_length=64)
    description = serializers.CharField(allow_blank=True, default="")
    image = serializers.CharField(max_length=256, allow_blank=True, default="")
    cpu_count = serializers.IntegerField(min_value=1, allow_null=True, default=None)
    memory_mb = serializers.IntegerField(min_value=1, allow_null=True, default=None)
    disk_size_mb = serializers.IntegerField(min_value=1, allow_null=True, default=None)
    timeout = serializers.IntegerField(min_value=1, allow_null=True, default=None)
    network = serializers.CharField(max_length=128, allow_blank=True, default="")
    region = serializers.CharField(max_length=64, allow_blank=True, default="")
    prewarm_count = serializers.IntegerField(min_value=0, allow_null=True, default=None)
    enabled = serializers.BooleanField(default=True)
    is_public = serializers.BooleanField(default=False)

    def to_internal_value(self, data):
        # 拼错的字段名会被静默丢弃并回落到默认值，比报错更难发现
        if isinstance(data, dict) and (unknown := set(data) - set(self.fields)):
            raise serializers.ValidationError(f"unknown fields: {', '.join(sorted(unknown))}")
        return super().to_internal_value(data)


def _format_errors(errors: dict | list) -> str:
    """单项的错误按字段给出；整项级别的错误（如未知字段）是列表"""
    if isinstance(errors, list):
        return " ".join(str(m) for m in errors)
    return "; ".join(f"{field}: {_format_errors(msgs)}" for field, msgs in errors.items())


class Command(BaseCommand):
    """Apply, enable, disable, delete or list the e2b sandbox templates.

    Only enabled templates can be used by the e2b SDK to create sandboxes. Among them,
    only the public ones are shown on the developer center, a non-public template is
    still usable by whoever knows its ID. The template itself lives on the e2b
    gateway, the ``template_id`` must match the gateway's.

    The templates are declared in a YAML file, a list of items with these keys:
    ``template_id`` and ``name`` (required), ``description``, ``image``, ``cpu_count``,
    ``memory_mb``, ``disk_size_mb``, ``timeout``, ``network``, ``region``,
    ``prewarm_count``, ``enabled`` (default true) and ``is_public`` (default false).
    For example:

        - template_id: e2b-envd
          name: Base
          is_public: true
          cpu_count: 2
          memory_mb: 4096

    Example:
        python manage.py e2b_sandbox_template apply -f e2b_templates.yaml
        python manage.py e2b_sandbox_template apply -f e2b_templates.yaml --prune
        python manage.py e2b_sandbox_template disable --template-id e2b-envd
        python manage.py e2b_sandbox_template delete --template-id e2b-envd --yes
        python manage.py e2b_sandbox_template list
    """

    help = "Manage the e2b sandbox templates registered on the platform"

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="action", required=True)

        apply = subparsers.add_parser(
            "apply", help="Create or overwrite the templates declared in a YAML file, others are left untouched"
        )
        apply.add_argument("-f", "--file", dest="file", required=True, help="Path of the YAML file")
        apply.add_argument("--prune", action="store_true", help="Disable the templates not declared in the file")

        for action in ("enable", "disable"):
            sub = subparsers.add_parser(action, help=f"{action.capitalize()} a template")
            sub.add_argument("--template-id", dest="template_id", required=True)

        delete = subparsers.add_parser("delete", help="Delete a template, running sandboxes are not affected")
        delete.add_argument("--template-id", dest="template_id", required=True)
        delete.add_argument("--yes", action="store_true", help="Confirm the deletion")

        subparsers.add_parser("list", help="List all templates")

    def handle(self, *args, **options):
        action = options["action"]
        if action == "apply":
            self._apply(options["file"], options["prune"])
        elif action in ("enable", "disable"):
            self._set_enabled(options["template_id"], enabled=action == "enable")
        elif action == "delete":
            self._delete(options["template_id"], options["yes"])
        else:
            self._list()

    def _apply(self, file: str, prune: bool):
        specs = self._load_specs(file)
        existing = {t.template_id: t for t in E2BSandboxTemplate.objects.all()}

        # 先校验整份文件再落库，并放在同一事务里，避免只生效一半
        with transaction.atomic():
            for template_id, spec in specs.items():
                template = existing.get(template_id)
                if template is None:
                    E2BSandboxTemplate.objects.create(template_id=template_id, **spec)
                    self.stdout.write(self.style.SUCCESS(f"Created template '{template_id}'"))
                    continue

                changed = [f for f, v in spec.items() if getattr(template, f) != v]
                if not changed:
                    self.stdout.write(f"Template '{template_id}' unchanged")
                    continue
                for field in changed:
                    setattr(template, field, spec[field])
                template.save(update_fields=[*changed, "updated"])
                self.stdout.write(self.style.SUCCESS(f"Updated template '{template_id}': {', '.join(changed)}"))

            if prune:
                for template_id, template in existing.items():
                    if template_id in specs or not template.enabled:
                        continue
                    template.enabled = False
                    template.save(update_fields=["enabled", "updated"])
                    self.stdout.write(self.style.WARNING(f"Disabled template '{template_id}' (not in file)"))

    @staticmethod
    def _load_specs(file: str) -> dict[str, dict]:
        """读取并校验声明文件，返回 template_id 到其余字段的映射"""
        try:
            data = yaml.safe_load(Path(file).read_text(encoding="utf-8"))
        except OSError as exc:
            raise CommandError(f"failed to read {file}: {exc}")
        except yaml.YAMLError as exc:
            raise CommandError(f"invalid YAML in {file}: {exc}")

        if not isinstance(data, list) or not data:
            raise CommandError(f"{file} must be a non-empty list of templates")

        slz = _TemplateSpecSLZ(data=data, many=True)
        if not slz.is_valid():
            problems = [f"  item #{idx}: {_format_errors(err)}" for idx, err in enumerate(slz.errors) if err]
            raise CommandError("invalid templates:\n" + "\n".join(problems))

        specs: dict[str, dict] = {}
        for item in slz.validated_data:
            spec = dict(item)
            template_id = spec.pop("template_id")
            if template_id in specs:
                raise CommandError(f"duplicated template_id in {file}: {template_id}")
            specs[template_id] = spec
        return specs

    def _set_enabled(self, template_id: str, enabled: bool):
        template = self._get_template(template_id)
        template.enabled = enabled
        template.save(update_fields=["enabled", "updated"])
        state = "enabled" if enabled else "disabled"
        self.stdout.write(self.style.SUCCESS(f"Template '{template_id}' is {state}"))

    def _delete(self, template_id: str, confirmed: bool):
        template = self._get_template(template_id)
        if not confirmed:
            raise CommandError(f"deleting template '{template_id}' needs --yes to confirm")
        template.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted template '{template_id}'"))

    def _list(self):
        templates = E2BSandboxTemplate.objects.all()
        if not templates:
            self.stdout.write("No templates registered")
            return

        for t in templates:
            self.stdout.write(
                f"{t.template_id}\tname={t.name}\tcpu_count={t.cpu_count}\tmemory_mb={t.memory_mb}\t"
                f"disk_size_mb={t.disk_size_mb}\ttimeout={t.timeout}\tenabled={t.enabled}\tis_public={t.is_public}"
            )

    @staticmethod
    def _get_template(template_id: str) -> E2BSandboxTemplate:
        try:
            return E2BSandboxTemplate.objects.get(template_id=template_id)
        except E2BSandboxTemplate.DoesNotExist:
            raise CommandError(f"Template '{template_id}' does not exist")
