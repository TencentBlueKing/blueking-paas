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

from paasng.platform.agent_sandbox.e2b.constants import (
    DEFAULT_TEMPLATE_CPU_COUNT,
    DEFAULT_TEMPLATE_MEMORY_MB,
    E2BSandboxStatus,
)
from paasng.platform.agent_sandbox.models import E2BSandbox, E2BSandboxTemplate
from tests.paasng.platform.agent_sandbox.e2b.helpers import IMAGE, make_builtin_template, make_custom_template

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

TEMPLATE_ID = "e2b-envd"


def _run(*args: str) -> str:
    out = StringIO()
    call_command("e2b_sandbox_template", *args, stdout=out)
    return out.getvalue()


@pytest.fixture()
def template() -> E2BSandboxTemplate:
    return make_builtin_template(TEMPLATE_ID, name="Base", description="old")


@pytest.fixture()
def write_file(tmp_path):
    def _write(content: str) -> str:
        path = tmp_path / "templates.yaml"
        path.write_text(content, encoding="utf-8")
        return str(path)

    return _write


class TestApply:
    def test_creates_builtin_templates(self, write_file):
        path = write_file(
            f"""
- template_id: e2b-envd
  name: Base
  image: {IMAGE}
  cpu_count: 4
  memory_mb: 2048
  env_vars: {{FOO: bar}}
  workdir: /home/user
  prewarm_count: 2
  is_public: true
- template_id: e2b-browser
  name: Browser
  image: {IMAGE}
"""
        )

        out = _run("apply", "-f", path)

        assert "Created template 'e2b-envd'" in out
        assert "Created template 'e2b-browser'" in out
        t = E2BSandboxTemplate.objects.get(template_id=TEMPLATE_ID)
        assert t.is_builtin
        assert t.resource_name == TEMPLATE_ID
        assert (t.cpu_count, t.memory_mb, t.env_vars, t.workdir, t.prewarm_count, t.is_public) == (
            4,
            2048,
            {"FOO": "bar"},
            "/home/user",
            2,
            True,
        )
        browser = E2BSandboxTemplate.objects.get(template_id="e2b-browser")
        assert (browser.cpu_count, browser.memory_mb, browser.disk_size_mb) == (
            DEFAULT_TEMPLATE_CPU_COUNT,
            DEFAULT_TEMPLATE_MEMORY_MB,
            None,
        )
        assert (browser.enabled, browser.is_public) == (True, False)

    def test_file_overwrites_existing(self, write_file, template):
        """文件即完整定义：文件里没写的字段要回到默认值，而不是沿用库里的旧值。"""
        template.cpu_count = 8
        template.save()

        out = _run("apply", "-f", write_file(f"- {{template_id: e2b-envd, name: Renamed, image: {IMAGE}}}"))

        template.refresh_from_db()
        assert template.name == "Renamed"
        assert template.cpu_count == DEFAULT_TEMPLATE_CPU_COUNT
        assert template.description == ""
        assert "Updated template 'e2b-envd'" in out

    def test_reapply_is_unchanged(self, write_file):
        path = write_file(f"- {{template_id: e2b-envd, name: Base, image: {IMAGE}}}")
        _run("apply", "-f", path)

        out = _run("apply", "-f", path)

        assert "Template 'e2b-envd' unchanged" in out

    def test_flags_follow_file(self, write_file, template):
        _run("apply", "-f", write_file(f"- {{template_id: e2b-envd, name: B, image: {IMAGE}, enabled: false}}"))
        template.refresh_from_db()
        assert (template.enabled, template.is_public) == (False, False)

        _run("apply", "-f", write_file(f"- {{template_id: e2b-envd, name: B, image: {IMAGE}, is_public: true}}"))
        template.refresh_from_db()
        assert (template.enabled, template.is_public) == (True, True)

    def test_leaves_undeclared_templates_alone(self, write_file, template):
        _run("apply", "-f", write_file(f"- {{template_id: e2b-browser, name: Browser, image: {IMAGE}}}"))

        template.refresh_from_db()
        assert template.enabled is True

    def test_prune_disables_undeclared_builtin_templates(self, write_file, template, bk_app):
        custom = make_custom_template(bk_app, "mine")

        out = _run(
            "apply", "-f", write_file(f"- {{template_id: e2b-browser, name: Browser, image: {IMAGE}}}"), "--prune"
        )

        template.refresh_from_db()
        custom.refresh_from_db()
        assert template.enabled is False
        assert custom.enabled is True
        assert "Disabled template 'e2b-envd' (not in file)" in out

    def test_rejects_id_taken_by_custom_template(self, write_file, bk_app):
        """资源名虽不冲突，但该应用按标识创建沙箱时就分不清用哪个了"""
        make_custom_template(bk_app, TEMPLATE_ID)

        with pytest.raises(CommandError, match="already used by a custom template"):
            _run("apply", "-f", write_file(f"- {{template_id: e2b-envd, name: Base, image: {IMAGE}}}"))

        assert not E2BSandboxTemplate.objects.builtins().exists()

    def test_failure_rolls_back_whole_file(self, write_file, template, bk_app):
        """入库时才发现的冲突也要整份回滚，已处理的项不能留下"""
        make_custom_template(bk_app, "e2b-browser")
        path = write_file(
            f"- {{template_id: e2b-envd, name: Renamed, image: {IMAGE}, cpu_count: 4}}\n"
            f"- {{template_id: e2b-new, name: New, image: {IMAGE}}}\n"
            f"- {{template_id: e2b-browser, name: Browser, image: {IMAGE}}}"
        )
        out = StringIO()

        with pytest.raises(CommandError, match="e2b-browser"):
            call_command("e2b_sandbox_template", "apply", "-f", path, stdout=out)

        template.refresh_from_db()
        assert (template.name, template.cpu_count) == ("Base", 2)
        assert not E2BSandboxTemplate.objects.filter(template_id="e2b-new").exists()
        assert out.getvalue() == ""

    @pytest.mark.parametrize(
        ("content", "message"),
        [
            (f"- {{template_id: e2b-envd, image: {IMAGE}}}", "name"),
            ("- {template_id: e2b-envd, name: Base}", "image"),
            (f"- {{template_id: e2b-envd, name: Base, image: {IMAGE}, cpu_count: 0}}", "cpu_count"),
            (f"- {{template_id: e2b-envd, name: Base, image: {IMAGE}, memory_mb: abc}}", "memory_mb"),
            (f"- {{template_id: e2b-envd, name: Base, image: {IMAGE}, prewarm_count: -1}}", "prewarm_count"),
            (f"- {{template_id: e2b--envd, name: Base, image: {IMAGE}}}", "template_id"),
            (f"- {{template_id: e2b-envd, name: Base, image: {IMAGE}, timeout: 60}}", "unknown fields: timeout"),
            (
                f"- {{template_id: ab, name: A, image: {IMAGE}}}\n- {{template_id: ab, name: B, image: x}}",
                "duplicated",
            ),
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
        path = write_file(
            f"- {{template_id: e2b-envd, name: Renamed, image: {IMAGE}}}\n"
            f"- {{template_id: e2b-browser, name: B, image: {IMAGE}, cpu_count: 0}}"
        )

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

    def test_custom_template_is_out_of_reach(self, bk_app):
        make_custom_template(bk_app, TEMPLATE_ID)

        with pytest.raises(CommandError, match="does not exist"):
            _run("disable", "--template-id", TEMPLATE_ID)


class TestDelete:
    def test_requires_confirmation(self, template):
        with pytest.raises(CommandError, match="--yes"):
            _run("delete", "--template-id", TEMPLATE_ID)

        assert E2BSandboxTemplate.objects.filter(template_id=TEMPLATE_ID).exists()

    def test_deletes(self, template):
        out = _run("delete", "--template-id", TEMPLATE_ID, "--yes")

        assert "Deleted template 'e2b-envd'" in out
        assert not E2BSandboxTemplate.objects.filter(template_id=TEMPLATE_ID).exists()

    def test_refuses_while_sandboxes_are_active(self, template, bk_app):
        """删除 SandboxPool 会连带销毁它名下正在运行的沙箱"""
        E2BSandbox.objects.create(
            sandbox_id="e2b-envd-20", application=bk_app, cluster_name="e2b-cluster", template_id=TEMPLATE_ID
        )

        with pytest.raises(CommandError, match="active sandboxes"):
            _run("delete", "--template-id", TEMPLATE_ID, "--yes")

        assert E2BSandboxTemplate.objects.filter(template_id=TEMPLATE_ID).exists()

    def test_terminated_sandboxes_do_not_block(self, template, bk_app):
        E2BSandbox.objects.create(
            sandbox_id="e2b-envd-20",
            application=bk_app,
            cluster_name="e2b-cluster",
            template_id=TEMPLATE_ID,
            status=E2BSandboxStatus.TERMINATED.value,
        )

        _run("delete", "--template-id", TEMPLATE_ID, "--yes")

        assert not E2BSandboxTemplate.objects.filter(template_id=TEMPLATE_ID).exists()

    def test_missing_template(self):
        with pytest.raises(CommandError, match="does not exist"):
            _run("delete", "--template-id", TEMPLATE_ID, "--yes")


class TestList:
    def test_lists_builtin_templates_with_state(self, template, bk_app):
        make_builtin_template("e2b-legacy", enabled=False, is_public=True)
        make_custom_template(bk_app, "mine")

        lines = _run("list").splitlines()

        assert len(lines) == 2
        assert lines[0].startswith("e2b-envd\t")
        assert f"image={IMAGE}" in lines[0]
        assert "enabled=True" in lines[0]
        assert "is_public=False" in lines[0]
        assert lines[1].startswith("e2b-legacy\t")
        assert "enabled=False" in lines[1]
        assert "is_public=True" in lines[1]

    def test_empty(self):
        assert "No templates registered" in _run("list")
