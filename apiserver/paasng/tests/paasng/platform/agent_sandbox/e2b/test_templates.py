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
from paasng.platform.agent_sandbox.e2b.constants import RESOURCE_NAME_MAX_LENGTH, E2BTemplateSyncStatus
from paasng.platform.agent_sandbox.e2b.exceptions import E2BTemplateAlreadyExists, E2BTemplateIDTooLong
from paasng.platform.agent_sandbox.models import E2BSandbox, E2BSandboxTemplate, E2BSandboxTemplateSyncRecord
from paasng.platform.applications.models import Application
from tests.utils.cluster import CLUSTER_NAME_FOR_TESTING

from .helpers import IMAGE, make_builtin_template, make_custom_template

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

# 服务层不补默认值，由序列化器负责
SPEC = {"name": "x", "image": IMAGE, "cpu_count": 2, "memory_mb": 4096, "disk_size_mb": 20480}


@pytest.fixture()
def sync_task():
    with mock.patch.object(templates, "sync_e2b_template_task") as task:
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

    def test_custom_ignores_prewarm_count(self, bk_app):
        template = templates.create_custom_template(bk_app, "mine", prewarm_count=3, **SPEC)

        assert template.prewarm_count == 0
        assert template.tenant_id == bk_app.tenant_id

    def test_sync_is_scheduled_after_commit(self, bk_app, sync_task, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks() as callbacks:
            template = templates.create_custom_template(bk_app, "mine", **SPEC)
            sync_task.delay.assert_not_called()

        assert len(callbacks) == 1
        callbacks[0]()
        sync_task.delay.assert_called_once_with(template.resource_name)

    @pytest.mark.usefixtures("e2b_config")
    def test_marks_target_clusters_pending(self, bk_app, sync_task):
        """任务还没跑时就要能看出未完成，否则与上一次的成功结果分不清"""
        template = templates.create_custom_template(bk_app, "mine", **SPEC)

        assert [(r.cluster_name, r.status) for r in template.sync_records.all()] == [
            (CLUSTER_NAME_FOR_TESTING, E2BTemplateSyncStatus.PENDING.value)
        ]


class TestUpdate:
    @pytest.mark.usefixtures("e2b_config")
    def test_marks_target_clusters_pending(self, sync_task):
        template = make_builtin_template("e2b-envd")
        E2BSandboxTemplateSyncRecord.objects.create(
            template=template, cluster_name=CLUSTER_NAME_FOR_TESTING, status=E2BTemplateSyncStatus.SUCCEEDED.value
        )

        templates.update_template(template, cpu_count=4)

        assert template.sync_records.get().status == E2BTemplateSyncStatus.PENDING.value

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

    def test_no_change_no_sync(self, sync_task, django_capture_on_commit_callbacks):
        template = make_builtin_template("e2b-envd")

        with django_capture_on_commit_callbacks(execute=True):
            templates.update_template(template, name=template.name)

        sync_task.delay.assert_not_called()

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

    @pytest.mark.parametrize("changes", [{"image": "mirrors.example.com/e2b/envd:v2"}, {"prewarm_count": 3}])
    def test_manifest_field_change_syncs(self, sync_task, django_capture_on_commit_callbacks, changes):
        template = make_builtin_template("e2b-envd")

        with django_capture_on_commit_callbacks(execute=True):
            templates.update_template(template, name="renamed", **changes)

        sync_task.delay.assert_called_once_with("e2b-envd")


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
        assert sorted(c.args[0] for c in sync_task.delay.call_args_list) == [
            f"{bk_app.code}--a",
            f"{bk_app.code}--b",
        ]
