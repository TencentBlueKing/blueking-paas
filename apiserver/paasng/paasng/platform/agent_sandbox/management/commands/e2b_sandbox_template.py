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

"""Command to manage the e2b builtin sandbox templates."""

from pathlib import Path

import yaml
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from rest_framework import serializers

from paasng.platform.agent_sandbox.e2b import templates
from paasng.platform.agent_sandbox.e2b.exceptions import (
    E2BTemplateAlreadyExists,
    E2BTemplateInUse,
    E2BTemplateSyncInProgress,
)
from paasng.platform.agent_sandbox.e2b.serializers import E2BBuiltinTemplateCreateInputSLZ
from paasng.platform.agent_sandbox.e2b.template_sync.sync import sync_all
from paasng.platform.agent_sandbox.models import E2BSandboxTemplate


class _TemplateSpecSLZ(E2BBuiltinTemplateCreateInputSLZ):
    """模板声明文件中的一项。未声明的字段取默认值，即文件就是该模板的完整定义。"""

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
    """Apply, enable, disable, delete, list or sync the e2b builtin sandbox templates.

    Builtin templates are usable by every application. Creating a template, or changing its spec,
    pushes it, as a SandboxTemplate and a SandboxPool of the same name, to every cluster with e2b
    enabled, asynchronously. Same-named CRs already in the cluster are overwritten. Only the public
    templates are shown on the developer center, a non-public one is still usable by whoever
    knows its ID.

    The templates are declared in a YAML file, a list of items with these keys:
    ``template_id``, ``name`` and ``image`` (required), ``description``, ``cpu_count``,
    ``memory_mb``, ``disk_size_mb``, ``env_vars``, ``workdir``, ``prewarm_count``,
    ``enabled`` (default true) and ``is_public`` (default false). For example:

        - template_id: e2b-envd
          name: Base
          image: mirrors.tencent.com/bcs/cube-base-envd:2026.16
          is_public: true
          cpu_count: 2
          memory_mb: 4096
          prewarm_count: 1

    Example:
        python manage.py e2b_sandbox_template apply -f e2b_templates.yaml
        python manage.py e2b_sandbox_template apply -f e2b_templates.yaml --prune
        python manage.py e2b_sandbox_template disable --template-id e2b-envd
        python manage.py e2b_sandbox_template delete --template-id e2b-envd --yes
        python manage.py e2b_sandbox_template list
        python manage.py e2b_sandbox_template sync
    """

    help = "Manage the e2b builtin sandbox templates"

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

        delete = subparsers.add_parser(
            "delete", help="Delete a template and its CRs, refused while it still has active sandboxes"
        )
        delete.add_argument("--template-id", dest="template_id", required=True)
        delete.add_argument("--yes", action="store_true", help="Confirm the deletion")

        subparsers.add_parser("list", help="List all builtin templates")
        subparsers.add_parser(
            "sync",
            help="Push all templates (custom ones included) to every e2b cluster and prune the CRs of deleted ones",
        )

    def handle(self, *args, **options):
        action = options["action"]
        if action == "apply":
            self._apply(options["file"], options["prune"])
        elif action in ("enable", "disable"):
            self._set_enabled(options["template_id"], enabled=action == "enable")
        elif action == "delete":
            self._delete(options["template_id"], options["yes"])
        elif action == "sync":
            self._sync()
        else:
            self._list()

    def _apply(self, file: str, prune: bool):
        specs = self._load_specs(file)
        # 整份文件一起生效：任一项失败全部回滚，下发任务在提交后才投递，结果也等提交后再输出
        messages: list[str] = []
        with transaction.atomic():
            existing = {t.template_id: t for t in E2BSandboxTemplate.objects.builtins()}

            for template_id, spec in specs.items():
                template = existing.get(template_id)
                if template is None:
                    try:
                        templates.create_builtin_template(template_id, **spec)
                    except E2BTemplateAlreadyExists:
                        raise CommandError(f"template_id '{template_id}' is already used by a custom template")
                    messages.append(self.style.SUCCESS(f"Created template '{template_id}'"))
                    continue

                changed = templates.update_template(template, **spec)
                if not changed:
                    messages.append(f"Template '{template_id}' unchanged")
                    continue
                messages.append(self.style.SUCCESS(f"Updated template '{template_id}': {', '.join(changed)}"))

            if prune:
                for template_id, template in existing.items():
                    if template_id in specs or not template.enabled:
                        continue
                    templates.update_template(template, enabled=False)
                    messages.append(self.style.WARNING(f"Disabled template '{template_id}' (not in file)"))

        for message in messages:
            self.stdout.write(message)

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
        templates.update_template(template, enabled=enabled)
        state = "enabled" if enabled else "disabled"
        self.stdout.write(self.style.SUCCESS(f"Template '{template_id}' is {state}"))

    def _delete(self, template_id: str, confirmed: bool):
        template = self._get_template(template_id)
        if not confirmed:
            raise CommandError(f"deleting template '{template_id}' needs --yes to confirm")
        try:
            templates.delete_template(template)
        except E2BTemplateInUse:
            raise CommandError(f"template '{template_id}' still has active sandboxes, destroy them first")
        self.stdout.write(self.style.SUCCESS(f"Deleted template '{template_id}'"))

    def _list(self):
        items = E2BSandboxTemplate.objects.builtins()
        if not items:
            self.stdout.write("No templates registered")
            return

        for t in items:
            self.stdout.write(
                f"{t.template_id}\tname={t.name}\timage={t.image}\tcpu_count={t.cpu_count}\t"
                f"memory_mb={t.memory_mb}\tdisk_size_mb={t.disk_size_mb}\tprewarm_count={t.prewarm_count}\t"
                f"enabled={t.enabled}\tis_public={t.is_public}"
            )

    def _sync(self):
        try:
            results = sync_all()
        except E2BTemplateSyncInProgress:
            raise CommandError("Another template sync is running, try again later")
        for result in results:
            if result.error:
                self.stdout.write(self.style.ERROR(f"[{result.cluster_name}] failed: {result.error}"))
                continue
            self.stdout.write(
                f"[{result.cluster_name}] synced={len(result.synced)} failed={len(result.failed)} "
                f"pruned={', '.join(result.pruned) or '-'}"
            )
            for resource_name, message in result.failed.items():
                self.stdout.write(self.style.ERROR(f"  {resource_name}: {message}"))

    @staticmethod
    def _get_template(template_id: str) -> E2BSandboxTemplate:
        template = E2BSandboxTemplate.objects.builtins().filter(template_id=template_id).first()
        if template is None:
            raise CommandError(f"Template '{template_id}' does not exist")
        return template
