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

"""开发者中心页面以登录态调用的 e2b 管理端点。"""

import uuid
from unittest import mock

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from paasng.platform.agent_sandbox.e2b import sandboxes
from paasng.platform.agent_sandbox.e2b.constants import MAX_ACTIVE_KEYS_PER_APP, E2BSandboxStatus
from paasng.platform.agent_sandbox.e2b.exceptions import E2BClusterNotConfigured, E2BGatewayTimeout
from paasng.platform.agent_sandbox.models import E2BApiKey, E2BSandbox, E2BSandboxTemplate
from paasng.platform.applications.models import Application
from tests.utils.auth import create_user

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

SANDBOX_ID = "e2b-envd-20"


def _key_list_url(app: Application) -> str:
    return reverse("agent_sandbox.e2b.console.api_key", kwargs={"code": app.code})


def _key_detail_url(app: Application, key_id) -> str:
    return reverse("agent_sandbox.e2b.console.api_key.destroy", kwargs={"code": app.code, "key_id": key_id})


def _sandbox_list_url(app: Application) -> str:
    return reverse("agent_sandbox.e2b.console.sandboxes", kwargs={"code": app.code})


def _sandbox_detail_url(app: Application, sandbox_id: str) -> str:
    return reverse("agent_sandbox.e2b.console.sandboxes.destroy", kwargs={"code": app.code, "sandbox_id": sandbox_id})


def _template_list_url(app: Application) -> str:
    return reverse("agent_sandbox.e2b.console.templates", kwargs={"code": app.code})


def _template_detail_url(app: Application, template_id: str) -> str:
    return reverse("agent_sandbox.e2b.console.templates.detail", kwargs={"code": app.code, "template_id": template_id})


def _gateway_item(sandbox_id: str = SANDBOX_ID, template_id: str = "e2b-envd") -> dict:
    """网关列表条目，带上不该下发给页面的字段，用来验证白名单。"""
    return {
        "sandboxID": sandbox_id,
        "templateID": template_id,
        "clientID": "client-xyz",
        "state": "running",
        "cpuCount": 2,
        "memoryMB": 4096,
        "diskSizeMB": 20480,
        "startedAt": "2026-09-07T13:02:31Z",
        "endAt": "2026-09-07T13:12:31Z",
        "envdVersion": "0.5.13",
        "domain": "e2b.example.com",
        "envdAccessToken": "secret-token",
    }


@pytest.fixture()
def outsider_client() -> APIClient:
    """已登录但不是应用成员的用户。"""
    client = APIClient()
    client.force_authenticate(user=create_user())
    return client


@pytest.fixture()
def e2b_sandbox(bk_app) -> E2BSandbox:
    """登记在 bk_app 名下的存活沙箱。"""
    return E2BSandbox.objects.create(
        sandbox_id=SANDBOX_ID, application=bk_app, cluster_name="e2b-cluster", tenant_id=bk_app.tenant_id
    )


class TestApiKeys:
    def test_create_returns_plaintext_once(self, api_client, bk_app):
        resp = api_client.post(_key_list_url(bk_app), data={"name": "ci"})

        assert resp.status_code == status.HTTP_201_CREATED
        body = resp.json()
        assert body["api_key"].startswith(body["key_prefix"])

        listed = api_client.get(_key_list_url(bk_app))
        assert body["api_key"] not in listed.content.decode()

    def test_list_includes_owner(self, api_client, bk_app, bk_user):
        api_client.post(_key_list_url(bk_app), data={"name": "ci"})

        (item,) = api_client.get(_key_list_url(bk_app)).json()

        assert set(item) == {"uuid", "name", "key_prefix", "created", "owner"}
        assert item["owner"] == bk_user.username

    def test_rejects_when_quota_exhausted(self, api_client, bk_app):
        for _ in range(MAX_ACTIVE_KEYS_PER_APP):
            assert api_client.post(_key_list_url(bk_app), data={}).status_code == status.HTTP_201_CREATED

        resp = api_client.post(_key_list_url(bk_app), data={})

        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_revoked_key_can_no_longer_authenticate(self, api_client, bk_app):
        body = api_client.post(_key_list_url(bk_app), data={}).json()

        resp = api_client.delete(_key_detail_url(bk_app, body["uuid"]))

        assert resp.status_code == status.HTTP_204_NO_CONTENT
        sdk_client = APIClient()
        sdk_client.credentials(HTTP_X_API_KEY=body["api_key"])
        assert sdk_client.get(reverse("agent_sandbox.e2b.sandboxes.list")).status_code == status.HTTP_401_UNAUTHORIZED

    def test_revoke_other_application_key_gets_404(self, api_client, bk_app, bk_app_full):
        key_id = api_client.post(_key_list_url(bk_app), data={}).json()["uuid"]

        resp = api_client.delete(_key_detail_url(bk_app_full, key_id))

        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert E2BApiKey.objects.get(uuid=key_id).enabled is True

    def test_revoke_unknown_key_gets_404(self, api_client, bk_app):
        assert api_client.delete(_key_detail_url(bk_app, uuid.uuid4())).status_code == status.HTTP_404_NOT_FOUND


class TestSandboxList:
    def test_outputs_whitelisted_fields(self, api_client, bk_app):
        with mock.patch.object(sandboxes, "list_sandboxes", return_value=[_gateway_item()]):
            resp = api_client.get(_sandbox_list_url(bk_app))

        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == [
            {
                "sandbox_id": SANDBOX_ID,
                "template_id": "e2b-envd",
                "state": "running",
                "cpu_count": 2,
                "memory_mb": 4096,
                "disk_size_mb": 20480,
                "started_at": "2026-09-07 21:02:31 +0800",
                "end_at": "2026-09-07 21:12:31 +0800",
            }
        ]

    def test_filters_by_template(self, api_client, bk_app):
        items = [_gateway_item("sb-1", "code"), _gateway_item("sb-2", "browser")]

        with mock.patch.object(sandboxes, "list_sandboxes", return_value=items):
            resp = api_client.get(_sandbox_list_url(bk_app), data={"template_id": "browser"})

        assert [item["sandbox_id"] for item in resp.json()] == ["sb-2"]

    def test_scoped_to_application(self, api_client, bk_app):
        with mock.patch.object(sandboxes, "list_sandboxes", return_value=[]) as list_sandboxes:
            api_client.get(_sandbox_list_url(bk_app))

        assert list_sandboxes.call_args.args[0] == bk_app


class TestSandboxDestroy:
    def test_kills_owned_sandbox(self, api_client, bk_app, e2b_sandbox):
        with mock.patch.object(sandboxes, "kill_sandbox") as kill:
            resp = api_client.delete(_sandbox_detail_url(bk_app, SANDBOX_ID))

        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert kill.call_args.args == (bk_app, SANDBOX_ID)

    def test_repeated_destroy_is_idempotent(self, api_client, bk_app, e2b_sandbox):
        """已终止的沙箱不再打网关，直接返回成功。"""
        e2b_sandbox.status = E2BSandboxStatus.TERMINATED.value
        e2b_sandbox.save(update_fields=["status"])

        resp = api_client.delete(_sandbox_detail_url(bk_app, SANDBOX_ID))

        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_other_application_sandbox_gets_404(self, api_client, bk_app_full, e2b_sandbox):
        resp = api_client.delete(_sandbox_detail_url(bk_app_full, SANDBOX_ID))

        assert resp.status_code == status.HTTP_404_NOT_FOUND
        e2b_sandbox.refresh_from_db()
        assert e2b_sandbox.status == E2BSandboxStatus.RUNNING.value

    @pytest.mark.parametrize(
        "exc",
        [
            E2BGatewayTimeout("gateway http://e2b-gateway.bcs-system:8080 timed out"),
            E2BClusterNotConfigured("cluster e2b-cluster has no e2b config"),
        ],
    )
    def test_service_errors_do_not_leak_internals(self, api_client, bk_app, e2b_sandbox, exc):
        with mock.patch.object(sandboxes, "kill_sandbox", side_effect=exc):
            resp = api_client.delete(_sandbox_detail_url(bk_app, SANDBOX_ID))

        assert resp.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "e2b-gateway" not in resp.content.decode()
        assert "e2b-cluster" not in resp.content.decode()


class TestTemplates:
    @pytest.fixture()
    def templates(self):
        E2BSandboxTemplate.objects.create(
            template_id="e2b-envd",
            name="Base",
            description="基础镜像",
            image="mirrors.example.com/e2b/envd:v1",
            cpu_count=2,
            memory_mb=4096,
            disk_size_mb=20480,
            timeout=600,
            network="内网",
            region="ieod",
            prewarm_count=3,
            is_public=True,
        )
        E2BSandboxTemplate.objects.create(template_id="e2b-legacy", name="Legacy", enabled=False, is_public=True)
        E2BSandboxTemplate.objects.create(template_id="e2b-internal", name="Internal")

    def test_list_only_enabled_and_public(self, api_client, bk_app, templates):
        resp = api_client.get(_template_list_url(bk_app))

        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == [
            {
                "template_id": "e2b-envd",
                "name": "Base",
                "description": "基础镜像",
                "cpu_count": 2,
                "memory_mb": 4096,
                "disk_size_mb": 20480,
                "timeout": 600,
            }
        ]

    def test_list_empty(self, api_client, bk_app):
        resp = api_client.get(_template_list_url(bk_app))

        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == []

    def test_detail_includes_extra_fields(self, api_client, bk_app, templates):
        resp = api_client.get(_template_detail_url(bk_app, "e2b-envd"))

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["template_id"] == "e2b-envd"
        assert body["image"] == "mirrors.example.com/e2b/envd:v1"
        assert body["network"] == "内网"
        assert body["region"] == "ieod"
        assert body["prewarm_count"] == 3

    @pytest.mark.parametrize("template_id", ["e2b-legacy", "e2b-internal", "not-registered"])
    def test_detail_of_unavailable_template_gets_404(self, api_client, bk_app, templates, template_id):
        resp = api_client.get(_template_detail_url(bk_app, template_id))

        assert resp.status_code == status.HTTP_404_NOT_FOUND


class TestPermission:
    @pytest.mark.parametrize(
        ("method", "url_factory"),
        [
            ("get", _key_list_url),
            ("post", _key_list_url),
            ("delete", lambda app: _key_detail_url(app, uuid.uuid4())),
            ("get", _sandbox_list_url),
            ("delete", lambda app: _sandbox_detail_url(app, SANDBOX_ID)),
            ("get", _template_list_url),
            ("get", lambda app: _template_detail_url(app, "e2b-envd")),
        ],
    )
    def test_outsider_is_forbidden(self, outsider_client, bk_app, method, url_factory):
        resp = getattr(outsider_client, method)(url_factory(bk_app))

        assert resp.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.parametrize(
        "url_factory",
        [_key_list_url, _template_list_url, lambda app: _template_detail_url(app, "e2b-envd")],
    )
    def test_anonymous_is_rejected(self, bk_app, url_factory):
        resp = APIClient().get(url_factory(bk_app))

        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_api_key_cannot_access_console(self, bk_app, bk_user):
        """协议端点用的 X-API-Key 不能拿来调页面端点。"""
        _, plain_key = E2BApiKey.objects.issue(application=bk_app, owner=bk_user.pk)
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=plain_key)

        resp = client.get(_key_list_url(bk_app))

        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
