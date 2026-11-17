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

from unittest import mock

import pytest
from django_dynamic_fixture import G

from paasng.platform.agent_sandbox.e2b import templates
from paasng.platform.agent_sandbox.e2b.constants import (
    RESOURCE_NAME_MAX_LENGTH,
    E2BSandboxStatus,
    E2BTemplateSyncStatus,
)
from paasng.platform.agent_sandbox.e2b.exceptions import (
    E2BAppCodeTooLong,
    E2BTemplateAlreadyExists,
    E2BTemplateIDTooLong,
    E2BTemplateInUse,
    E2BTemplateNotFound,
)
from paasng.platform.agent_sandbox.models import E2BSandbox, E2BSandboxTemplate, E2BSandboxTemplateSyncRecord
from paasng.platform.applications.models import Application
from tests.utils.cluster import CLUSTER_NAME_FOR_TESTING

from .helpers import IMAGE, make_builtin_template, make_custom_template

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

# 服务层不补默认值，由序列化器负责
SPEC = {"name": "x", "image": IMAGE, "cpu_count": 2, "memory_mb": 4096, "disk_size_mb": 20480}


@pytest.fixture()
def sync_task():
    with mock.patch.object(templates, "sync_e2b_templates_task") as task:
        yield task


class TestResourceName:
    def test_smart_app_code_is_escaped(self):
        """S-mart 应用 code 允许下划线，k8s 资源名不接受"""
        app = Application(code="My_App")

        assert templates.make_custom_resource_name(app, "tpl") == "my0us0app--tpl"

    @pytest.mark.parametrize(
        ("resource_name", "expected"),
        [("demo--tpl", "tpl"), ("e2b-envd", "e2b-envd"), ("other--tpl", "other--tpl")],
    )
    def test_to_sdk_template_id(self, resource_name, expected):
        assert templates.to_sdk_template_id(Application(code="demo"), resource_name) == expected


class TestCreate:
    def test_builtin_rejects_duplicate(self):
        make_builtin_template("e2b-envd")

        with pytest.raises(E2BTemplateAlreadyExists):
            templates.create_builtin_template("e2b-envd", **SPEC)

    def test_custom_rejects_overlong_resource_name(self, sync_task):
        """应用前缀转义后会变长，标识本身合法也可能超出资源名上限"""
        app = G(Application, code="ab_cd_ef_gh_ij_kl_mn")

        with pytest.raises(E2BTemplateIDTooLong, match="at most 23 characters"):
            templates.create_custom_template(app, "a" * 24, **SPEC)

        template = templates.create_custom_template(app, "a" * 23, **SPEC)
        assert len(template.resource_name) == RESOURCE_NAME_MAX_LENGTH

    def test_custom_allows_min_length_id_with_longest_usable_prefix(self):
        """前缀 61 个字符，余下的长度恰好放得下最短的标识"""
        app = G(Application, code="a" * 7 + "_" * 13)
        assert len(templates.get_custom_resource_prefix(app)) == 61

        with pytest.raises(E2BTemplateIDTooLong, match="at most 2 characters"):
            templates.create_custom_template(app, "abc", **SPEC)
        assert templates.create_custom_template(app, "ab", **SPEC).resource_name.endswith("--ab")

    @pytest.mark.parametrize("code", ["a" * 4 + "_" * 14, "a" + "_" * 19])
    def test_custom_rejects_app_whose_prefix_leaves_no_room(self, code):
        app = G(Application, code=code)

        with pytest.raises(E2BAppCodeTooLong):
            templates.create_custom_template(app, "ab", **SPEC)

    def test_custom_ignores_prewarm_count(self, bk_app):
        template = templates.create_custom_template(bk_app, "mine", prewarm_count=3, **SPEC)

        assert template.prewarm_count == 0
        assert template.tenant_id == bk_app.tenant_id

    @pytest.mark.usefixtures("e2b_config")
    def test_marks_pending_and_schedules_sync_after_commit(
        self, bk_app, sync_task, django_capture_on_commit_callbacks
    ):
        """任务还没跑时就要能看出未完成，否则与上一次的成功结果分不清"""
        with django_capture_on_commit_callbacks() as callbacks:
            template = templates.create_custom_template(bk_app, "mine", **SPEC)
            sync_task.delay.assert_not_called()

        assert [(r.cluster_name, r.status) for r in template.sync_records.all()] == [
            (CLUSTER_NAME_FOR_TESTING, E2BTemplateSyncStatus.PENDING.value)
        ]
        assert len(callbacks) == 1
        callbacks[0]()
        sync_task.delay.assert_called_once_with(resource_names=[template.resource_name])


class TestUpdate:
    def test_returns_changed_fields(self):
        template = make_builtin_template("e2b-envd")

        changed = templates.update_template(template, name="e2b-envd", cpu_count=4, prewarm_count=2)

        assert changed == ["cpu_count", "prewarm_count"]
        template.refresh_from_db()
        assert (template.cpu_count, template.prewarm_count) == (4, 2)

    def test_custom_template_ignores_builtin_only_fields(self, bk_app):
        template = make_custom_template(bk_app, "mine")

        changed = templates.update_template(template, prewarm_count=5, is_public=True, enabled=False)

        assert changed == []
        template.refresh_from_db()
        assert (template.prewarm_count, template.is_public, template.enabled) == (0, False, True)

    @pytest.mark.usefixtures("e2b_config")
    def test_fields_outside_manifest_no_sync(self, sync_task, django_capture_on_commit_callbacks):
        """名称、描述、启用、公开都不进 CR，改了不必下发，也不能把下发记录打回待同步"""
        template = make_builtin_template("e2b-envd")
        E2BSandboxTemplateSyncRecord.objects.create(
            template=template, cluster_name=CLUSTER_NAME_FOR_TESTING, status=E2BTemplateSyncStatus.SUCCEEDED.value
        )

        with django_capture_on_commit_callbacks(execute=True):
            changed = templates.update_template(
                template, name="renamed", description="new", enabled=False, is_public=True
            )

        assert sorted(changed) == ["description", "enabled", "is_public", "name"]
        sync_task.delay.assert_not_called()
        assert template.sync_records.get().status == E2BTemplateSyncStatus.SUCCEEDED.value

    @pytest.mark.usefixtures("e2b_config")
    @pytest.mark.parametrize("changes", [{"image": "mirrors.example.com/e2b/envd:v2"}, {"prewarm_count": 3}])
    def test_manifest_field_change_syncs(self, sync_task, django_capture_on_commit_callbacks, changes):
        template = make_builtin_template("e2b-envd")
        E2BSandboxTemplateSyncRecord.objects.create(
            template=template, cluster_name=CLUSTER_NAME_FOR_TESTING, status=E2BTemplateSyncStatus.SUCCEEDED.value
        )

        with django_capture_on_commit_callbacks(execute=True):
            templates.update_template(template, name="renamed", **changes)

        assert template.sync_records.get().status == E2BTemplateSyncStatus.PENDING.value
        sync_task.delay.assert_called_once_with(resource_names=["e2b-envd"])


class TestGetUsable:
    def test_rejects_custom_and_builtin_with_same_id(self, bk_app, bk_app_full):
        """创建时的重名检查是先查后写，并发下可能留下同名的内置与自定义模板"""
        builtin = make_builtin_template("a")
        make_custom_template(bk_app, "a")

        with pytest.raises(E2BSandboxTemplate.MultipleObjectsReturned):
            E2BSandboxTemplate.objects.get_usable(bk_app, "a")
        assert E2BSandboxTemplate.objects.get_usable(bk_app_full, "a") == builtin

    def test_custom_template_of_other_app_is_not_usable(self, bk_app, bk_app_full):
        make_custom_template(bk_app, "a")

        with pytest.raises(E2BTemplateNotFound):
            E2BSandboxTemplate.objects.get_usable(bk_app_full, "a")


class TestDelete:
    def test_custom_template_in_use_is_rejected(self, bk_app):
        """沙箱登记的是资源名，自定义模板的资源名与标识不同"""
        template = make_custom_template(bk_app, "a")
        assert template.resource_name != template.template_id
        E2BSandbox.objects.create(
            sandbox_id="sb-1", application=bk_app, cluster_name="c", template_id=template.resource_name
        )

        with pytest.raises(E2BTemplateInUse):
            templates.delete_template(template)
        assert E2BSandboxTemplate.objects.filter(pk=template.pk).exists()

    def test_same_template_id_of_other_app_does_not_block(self, bk_app, bk_app_full):
        mine = make_custom_template(bk_app, "a")
        theirs = make_custom_template(bk_app_full, "a")
        E2BSandbox.objects.create(
            sandbox_id="sb-1", application=bk_app_full, cluster_name="c", template_id=theirs.resource_name
        )

        templates.delete_template(mine)

        assert not E2BSandboxTemplate.objects.filter(pk=mine.pk).exists()

    def test_terminated_sandboxes_do_not_block(self, bk_app):
        template = make_custom_template(bk_app, "a")
        E2BSandbox.objects.create(
            sandbox_id="sb-1",
            application=bk_app,
            cluster_name="c",
            template_id=template.resource_name,
            status=E2BSandboxStatus.TERMINATED.value,
        )

        templates.delete_template(template)

        assert not E2BSandboxTemplate.objects.filter(pk=template.pk).exists()


class TestDeleteCustomTemplatesOf:
    def test_deletes_all_regardless_of_sandboxes(
        self, bk_app, bk_app_full, sync_task, django_capture_on_commit_callbacks
    ):
        """应用删除时沙箱随之作废，不再拦截"""
        mine = make_custom_template(bk_app, "a")
        make_custom_template(bk_app, "b")
        theirs = make_custom_template(bk_app_full, "a")
        builtin = make_builtin_template("e2b-envd")
        E2BSandbox.objects.create(
            sandbox_id="sb-1", application=bk_app, cluster_name="c", template_id=mine.resource_name
        )

        with django_capture_on_commit_callbacks(execute=True):
            templates.delete_custom_templates_of(bk_app)

        assert set(E2BSandboxTemplate.objects.values_list("pk", flat=True)) == {theirs.pk, builtin.pk}
        assert sorted(c.kwargs["resource_names"][0] for c in sync_task.delay.call_args_list) == [
            f"{bk_app.code}--a",
            f"{bk_app.code}--b",
        ]
