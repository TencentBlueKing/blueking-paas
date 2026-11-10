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

"""应用侧的 e2b 沙箱模板接口：开发者中心页面与 APIGW 两个入口，行为一致。"""

from types import SimpleNamespace
from unittest import mock

import pytest
from django.urls import reverse
from rest_framework import status

from paasng.platform.agent_sandbox.e2b.constants import E2BSandboxStatus
from paasng.platform.agent_sandbox.e2b.serializers import E2BCustomTemplateCreateInputSLZ
from paasng.platform.agent_sandbox.models import E2BSandbox, E2BSandboxTemplate
from paasng.platform.applications.models import Application
from tests.paasng.platform.agent_sandbox.e2b.helpers import IMAGE, make_builtin_template, make_custom_template

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


def _list_url(app: Application) -> str:
    return reverse("agent_sandbox.e2b.console.templates", kwargs={"code": app.code})


def _detail_url(app: Application, template_id: str) -> str:
    return reverse("agent_sandbox.e2b.console.templates.detail", kwargs={"code": app.code, "template_id": template_id})


@pytest.fixture()
def visible_templates(bk_app, bk_app_full):
    """bk_app 能看到的只有 public 与 mine"""
    make_builtin_template("public", is_public=True)
    make_builtin_template("internal", is_public=False)
    make_builtin_template("legacy", is_public=True, enabled=False)
    make_custom_template(bk_app, "mine", env_vars={"FOO": "bar"})
    make_custom_template(bk_app_full, "theirs")


class TestList:
    def test_lists_public_builtin_and_own_custom(self, api_client, bk_app, visible_templates):
        resp = api_client.get(_list_url(bk_app))

        assert resp.status_code == status.HTTP_200_OK
        assert [(t["template_id"], t["is_builtin"]) for t in resp.json()] == [("mine", False), ("public", True)]

    def test_item_fields(self, api_client, bk_app, visible_templates):
        (item, _) = api_client.get(_list_url(bk_app)).json()

        assert item == {
            "template_id": "mine",
            "is_builtin": False,
            "name": "mine",
            "description": "",
            "image": IMAGE,
            "cpu_count": 2,
            "memory_mb": 4096,
            "disk_size_mb": 20480,
        }


class TestRetrieve:
    def test_own_custom_template_shows_env_vars(self, api_client, bk_app, visible_templates):
        resp = api_client.get(_detail_url(bk_app, "mine"))

        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["env_vars"] == {"FOO": "bar"}

    def test_builtin_template_hides_env_vars(self, api_client, bk_app):
        make_builtin_template("public", is_public=True, env_vars={"TOKEN": "secret"})

        resp = api_client.get(_detail_url(bk_app, "public"))

        assert resp.json()["env_vars"] == {}

    @pytest.mark.parametrize("template_id", ["internal", "legacy", "theirs", "not-exists"])
    def test_invisible_template_gets_404(self, api_client, bk_app, visible_templates, template_id):
        resp = api_client.get(_detail_url(bk_app, template_id))

        assert resp.status_code == status.HTTP_404_NOT_FOUND


class TestCreate:
    def test_creates_custom_template(self, api_client, bk_app, django_capture_on_commit_callbacks):
        with (
            mock.patch("paasng.platform.agent_sandbox.e2b.templates.sync_e2b_template_task") as task,
            django_capture_on_commit_callbacks(execute=True),
        ):
            resp = api_client.post(
                _list_url(bk_app), data={"template_id": "my-tpl", "name": "Mine", "image": IMAGE}, format="json"
            )

        assert resp.status_code == status.HTTP_201_CREATED
        template = E2BSandboxTemplate.objects.get(application=bk_app, template_id="my-tpl")
        assert not template.is_builtin
        assert template.resource_name == f"{bk_app.code}--my-tpl"
        assert (template.cpu_count, template.memory_mb, template.disk_size_mb) == (2, 4096, None)
        task.delay.assert_called_once_with(template.resource_name)

    @pytest.mark.parametrize("template_id", ["internal", "public", "mine"])
    def test_rejects_taken_template_id(self, api_client, bk_app, visible_templates, template_id):
        """与内置模板重名也不行，包括不公开的：任意应用都能按标识使用它们"""
        resp = api_client.post(
            _list_url(bk_app), data={"template_id": template_id, "name": "x", "image": IMAGE}, format="json"
        )

        assert resp.status_code == status.HTTP_409_CONFLICT

    def test_same_template_id_in_another_app_is_allowed(self, api_client, bk_app, visible_templates):
        resp = api_client.post(
            _list_url(bk_app), data={"template_id": "theirs", "name": "x", "image": IMAGE}, format="json"
        )

        assert resp.status_code == status.HTTP_201_CREATED

    def test_rejects_when_quota_exhausted(self, api_client, bk_app, settings):
        settings.AGENT_SANDBOX_E2B_MAX_CUSTOM_TEMPLATES_PER_APP = 1
        make_custom_template(bk_app, "first")

        resp = api_client.post(
            _list_url(bk_app), data={"template_id": "second", "name": "x", "image": IMAGE}, format="json"
        )

        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize("template_id", ["a--b", "Upper", "-lead", "trail-", "1st", "x", "a" * 32])
    def test_rejects_invalid_template_id(self, api_client, bk_app, template_id):
        resp = api_client.post(
            _list_url(bk_app), data={"template_id": template_id, "name": "x", "image": IMAGE}, format="json"
        )

        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize(("template_id", "valid"), [("a" * 11, True), ("a" * 12, False)])
    def test_resource_name_must_fit_label_value(self, template_id, valid):
        """资源名会写进标签值，不能超过 63 个字符；S-mart 应用 code 里的下划线转义后会变长"""
        app = SimpleNamespace(code="a_" * 10)
        slz = E2BCustomTemplateCreateInputSLZ(
            data={"template_id": template_id, "name": "x", "image": IMAGE}, context={"application": app}
        )

        assert slz.is_valid() is valid

    @pytest.mark.parametrize(
        "extra",
        [
            {"env_vars": {"1BAD": "x"}},
            {"workdir": "relative/path"},
            {"cpu_count": 0},
            {"memory_mb": 1},
        ],
    )
    def test_rejects_invalid_spec(self, api_client, bk_app, extra):
        data = {"template_id": "my-tpl", "name": "x", "image": IMAGE, **extra}

        resp = api_client.post(_list_url(bk_app), data=data, format="json")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST


class TestUpdate:
    def test_updates_own_custom_template(self, api_client, bk_app, django_capture_on_commit_callbacks):
        template = make_custom_template(bk_app, "mine")

        with (
            mock.patch("paasng.platform.agent_sandbox.e2b.templates.sync_e2b_template_task") as task,
            django_capture_on_commit_callbacks(execute=True),
        ):
            resp = api_client.put(
                _detail_url(bk_app, "mine"),
                data={"name": "Mine", "image": "new:v2", "cpu_count": 4, "env_vars": {"A": "1"}},
                format="json",
            )

        assert resp.status_code == status.HTTP_200_OK
        template.refresh_from_db()
        assert (template.image, template.cpu_count, template.env_vars) == ("new:v2", 4, {"A": "1"})
        task.delay.assert_called_once_with(template.resource_name)

    @pytest.mark.parametrize("template_id", ["public", "theirs"])
    def test_cannot_update_builtin_or_others(self, api_client, bk_app, visible_templates, template_id):
        resp = api_client.put(_detail_url(bk_app, template_id), data={"name": "x", "image": IMAGE}, format="json")

        assert resp.status_code == status.HTTP_404_NOT_FOUND


class TestDestroy:
    def test_deletes_own_custom_template(self, api_client, bk_app, django_capture_on_commit_callbacks):
        template = make_custom_template(bk_app, "mine")

        with (
            mock.patch("paasng.platform.agent_sandbox.e2b.templates.sync_e2b_template_task") as task,
            django_capture_on_commit_callbacks(execute=True),
        ):
            resp = api_client.delete(_detail_url(bk_app, "mine"))

        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not E2BSandboxTemplate.objects.filter(pk=template.pk).exists()
        task.delay.assert_called_once_with(template.resource_name)

    def test_refuses_while_sandboxes_are_active(self, api_client, bk_app):
        """删除池子会连带销毁正在用的沙箱"""
        template = make_custom_template(bk_app, "mine")
        E2BSandbox.objects.create(
            sandbox_id="sb-1", application=bk_app, cluster_name="c1", template_id=template.resource_name
        )

        resp = api_client.delete(_detail_url(bk_app, "mine"))

        assert resp.status_code == status.HTTP_409_CONFLICT
        assert E2BSandboxTemplate.objects.filter(pk=template.pk).exists()

    def test_terminated_sandboxes_do_not_block(self, api_client, bk_app):
        template = make_custom_template(bk_app, "mine")
        E2BSandbox.objects.create(
            sandbox_id="sb-1",
            application=bk_app,
            cluster_name="c1",
            template_id=template.resource_name,
            status=E2BSandboxStatus.TERMINATED.value,
        )

        resp = api_client.delete(_detail_url(bk_app, "mine"))

        assert resp.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.parametrize("template_id", ["public", "theirs"])
    def test_cannot_delete_builtin_or_others(self, api_client, bk_app, visible_templates, template_id):
        resp = api_client.delete(_detail_url(bk_app, template_id))

        assert resp.status_code == status.HTTP_404_NOT_FOUND


class TestApigwEntry:
    def test_requires_verified_app(self, api_client, bk_app):
        resp = api_client.get(reverse("agent_sandbox.e2b.templates", kwargs={"code": bk_app.code}))

        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_lists_templates(self, api_client, bk_app, visible_templates):
        with (
            mock.patch("paasng.platform.agent_sandbox.e2b.views.IsAPIGWVerifiedApp.has_permission", return_value=True),
            mock.patch(
                "paasng.platform.agent_sandbox.e2b.views.IsAPIGWVerifiedApp.has_object_permission",
                return_value=True,
            ),
        ):
            resp = api_client.get(reverse("agent_sandbox.e2b.templates", kwargs={"code": bk_app.code}))

        assert resp.status_code == status.HTTP_200_OK
        assert [t["template_id"] for t in resp.json()] == ["mine", "public"]
