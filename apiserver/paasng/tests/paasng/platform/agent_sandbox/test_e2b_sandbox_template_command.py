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

from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from paasng.platform.agent_sandbox.models import E2BSandbox, E2BSandboxTemplate

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

TEMPLATE_ID = "e2b-envd"


def _run(*args: str) -> str:
    out = StringIO()
    call_command("e2b_sandbox_template", *args, stdout=out)
    return out.getvalue()


@pytest.fixture()
def template() -> E2BSandboxTemplate:
    return E2BSandboxTemplate.objects.create(
        template_id=TEMPLATE_ID, name="Base", description="old", cpu_count=2, memory_mb=4096
    )


@pytest.fixture()
def write_file(tmp_path):
    def _write(content: str) -> str:
        path = tmp_path / "templates.yaml"
        path.write_text(content, encoding="utf-8")
        return str(path)

    return _write


class TestApply:
    def test_creates_with_defaults(self, write_file):
        path = write_file(
            """
- template_id: e2b-envd
  name: Base
  cpu_count: 2
  memory_mb: 4096
  disk_size_mb: 20480
  timeout: 600
  prewarm_count: 0
- template_id: e2b-browser
  name: Browser
"""
        )

        out = _run("apply", "-f", path)

        assert "Created template 'e2b-envd'" in out
        assert "Created template 'e2b-browser'" in out
        t = E2BSandboxTemplate.objects.get(template_id=TEMPLATE_ID)
        assert (t.name, t.cpu_count, t.memory_mb, t.disk_size_mb, t.timeout, t.prewarm_count) == (
            "Base",
            2,
            4096,
            20480,
            600,
            0,
        )
        assert t.enabled is True
        assert t.is_public is False
        assert t.image == ""

    def test_file_overwrites_existing(self, write_file, template):
        """文件即完整定义：文件里没写的字段要回到默认值，而不是沿用库里的旧值。"""
        path = write_file("- {template_id: e2b-envd, name: Renamed, memory_mb: 8192}")

        out = _run("apply", "-f", path)

        template.refresh_from_db()
        assert template.name == "Renamed"
        assert template.memory_mb == 8192
        assert template.cpu_count is None
        assert template.description == ""
        assert "Updated template 'e2b-envd'" in out

    def test_reapply_is_unchanged(self, write_file):
        path = write_file("- {template_id: e2b-envd, name: Base, cpu_count: 2}")
        _run("apply", "-f", path)

        out = _run("apply", "-f", path)

        assert "Template 'e2b-envd' unchanged" in out

    def test_enabled_follows_file(self, write_file, template):
        path = write_file("- {template_id: e2b-envd, name: Base, enabled: false}")
        _run("apply", "-f", path)
        template.refresh_from_db()
        assert template.enabled is False

        _run("apply", "-f", write_file("- {template_id: e2b-envd, name: Base}"))
        template.refresh_from_db()
        assert template.enabled is True

    def test_is_public_follows_file(self, write_file, template):
        _run("apply", "-f", write_file("- {template_id: e2b-envd, name: Base, is_public: true}"))
        template.refresh_from_db()
        assert template.is_public is True

        _run("apply", "-f", write_file("- {template_id: e2b-envd, name: Base}"))
        template.refresh_from_db()
        assert template.is_public is False

    def test_leaves_undeclared_templates_alone(self, write_file, template):
        _run("apply", "-f", write_file("- {template_id: e2b-browser, name: Browser}"))

        template.refresh_from_db()
        assert template.enabled is True

    def test_prune_disables_undeclared_templates(self, write_file, template):
        out = _run("apply", "-f", write_file("- {template_id: e2b-browser, name: Browser}"), "--prune")

        template.refresh_from_db()
        assert template.enabled is False
        assert "Disabled template 'e2b-envd' (not in file)" in out

    @pytest.mark.parametrize(
        ("content", "message"),
        [
            ("- {template_id: e2b-envd, cpu_count: 2}", "name"),
            ("- {template_id: e2b-envd, name: Base, cpu_count: 0}", "cpu_count"),
            ("- {template_id: e2b-envd, name: Base, memory_mb: abc}", "memory_mb"),
            ("- {template_id: e2b-envd, name: Base, prewarm_count: -1}", "prewarm_count"),
            ("- {template_id: e2b-envd, name: Base, memory: 4096}", "unknown fields: memory"),
            ("- {template_id: a, name: A}\n- {template_id: a, name: B}", "duplicated template_id"),
            ("[]", "non-empty list"),
            ("template_id: e2b-envd", "non-empty list"),
            ("- [unclosed", "invalid YAML"),
        ],
    )
    def test_rejects_invalid_file(self, write_file, content, message):
        with pytest.raises(CommandError, match=message):
            _run("apply", "-f", write_file(content))

        assert not E2BSandboxTemplate.objects.exists()

    def test_invalid_item_aborts_whole_file(self, write_file, template):
        """一项不合法则整份文件都不生效，不能只应用一半。"""
        path = write_file("- {template_id: e2b-envd, name: Renamed}\n- {template_id: e2b-browser, cpu_count: 0}")

        with pytest.raises(CommandError, match="item #1"):
            _run("apply", "-f", path)

        template.refresh_from_db()
        assert template.name == "Base"
        assert not E2BSandboxTemplate.objects.filter(template_id="e2b-browser").exists()

    def test_missing_file(self, tmp_path):
        with pytest.raises(CommandError, match="failed to read"):
            _run("apply", "-f", str(tmp_path / "nope.yaml"))


class TestEnableDisable:
    def test_toggle(self, template):
        _run("disable", "--template-id", TEMPLATE_ID)
        template.refresh_from_db()
        assert template.enabled is False

        _run("enable", "--template-id", TEMPLATE_ID)
        template.refresh_from_db()
        assert template.enabled is True

    @pytest.mark.parametrize("action", ["enable", "disable"])
    def test_missing_template(self, action):
        with pytest.raises(CommandError, match="does not exist"):
            _run(action, "--template-id", TEMPLATE_ID)


class TestDelete:
    def test_requires_confirmation(self, template):
        with pytest.raises(CommandError, match="--yes"):
            _run("delete", "--template-id", TEMPLATE_ID)

        assert E2BSandboxTemplate.objects.filter(template_id=TEMPLATE_ID).exists()

    def test_delete_keeps_running_sandboxes(self, template, bk_app):
        sandbox = E2BSandbox.objects.create(
            sandbox_id="e2b-envd-20",
            application=bk_app,
            cluster_name="e2b-cluster",
            template_id=TEMPLATE_ID,
            tenant_id=bk_app.tenant_id,
        )

        _run("delete", "--template-id", TEMPLATE_ID, "--yes")

        assert not E2BSandboxTemplate.objects.filter(template_id=TEMPLATE_ID).exists()
        sandbox.refresh_from_db()
        assert sandbox.template_id == TEMPLATE_ID

    def test_missing_template(self):
        with pytest.raises(CommandError, match="does not exist"):
            _run("delete", "--template-id", TEMPLATE_ID, "--yes")


class TestList:
    def test_lists_all_with_state(self, template):
        E2BSandboxTemplate.objects.create(template_id="e2b-legacy", name="Legacy", enabled=False, is_public=True)

        lines = _run("list").splitlines()

        assert len(lines) == 2
        assert lines[0].startswith("e2b-envd\t")
        assert "cpu_count=2" in lines[0]
        assert "enabled=True" in lines[0]
        assert "is_public=False" in lines[0]
        assert lines[1].startswith("e2b-legacy\t")
        assert "enabled=False" in lines[1]
        assert "is_public=True" in lines[1]

    def test_empty(self):
        assert "No templates registered" in _run("list")
