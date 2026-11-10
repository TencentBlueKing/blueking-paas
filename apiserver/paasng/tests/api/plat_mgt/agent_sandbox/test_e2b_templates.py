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
from django.urls import reverse
from django_dynamic_fixture import G
from rest_framework import status

from paas_wl.infras.cluster.models import Cluster, ClusterE2BConfig
from paasng.core.tenant.user import DEFAULT_TENANT_ID
from paasng.misc.audit.constants import OperationTarget
from paasng.misc.audit.models import AdminOperationRecord
from paasng.platform.agent_sandbox.e2b.constants import E2BTemplateSyncStatus
from paasng.platform.agent_sandbox.e2b.template_sync import ClusterSyncResult
from paasng.platform.agent_sandbox.models import E2BSandbox, E2BSandboxTemplate, E2BSandboxTemplateSyncRecord
from tests.paasng.platform.agent_sandbox.e2b.helpers import IMAGE, make_builtin_template, make_custom_template
from tests.utils.cluster import CLUSTER_NAME_FOR_TESTING

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

LIST_URL = reverse("plat_mgt.agent_sandbox.e2b.templates.list_create")
SYNC_URL = reverse("plat_mgt.agent_sandbox.e2b.template_sync")
SYNC_TEMPLATES_URL = reverse("plat_mgt.agent_sandbox.e2b.template_sync.templates")
SYNC_CLUSTERS_URL = reverse("plat_mgt.agent_sandbox.e2b.template_sync.clusters")
OTHER_CLUSTER = "e2b-other-cluster"


def _detail_url(template_id: str) -> str:
    return reverse("plat_mgt.agent_sandbox.e2b.templates.retrieve_update_destroy", kwargs={"template_id": template_id})


@pytest.fixture(autouse=True)
def sync_task():
    with mock.patch("paasng.platform.agent_sandbox.e2b.templates.sync_e2b_template_task") as task:
        yield task


def _audited() -> bool:
    return AdminOperationRecord.objects.filter(target=OperationTarget.E2B_SANDBOX_TEMPLATE.value).exists()


class TestList:
    def test_lists_builtin_only(self, plat_mgt_api_client, bk_app):
        make_builtin_template("e2b-envd", is_public=False, env_vars={"A": "1"})
        make_custom_template(bk_app, "mine")

        resp = plat_mgt_api_client.get(LIST_URL)

        assert resp.status_code == status.HTTP_200_OK
        (item,) = resp.json()
        assert item["template_id"] == "e2b-envd"
        assert item["env_vars"] == {"A": "1"}
        assert item["is_public"] is False

    def test_custom_template_is_not_reachable(self, plat_mgt_api_client, bk_app):
        make_custom_template(bk_app, "mine")

        assert plat_mgt_api_client.get(_detail_url("mine")).status_code == status.HTTP_404_NOT_FOUND


class TestCreate:
    def test_creates_builtin(self, plat_mgt_api_client, sync_task, django_capture_on_commit_callbacks):
        data = {"template_id": "e2b-envd", "name": "Base", "image": IMAGE, "prewarm_count": 2, "is_public": True}

        with django_capture_on_commit_callbacks(execute=True):
            resp = plat_mgt_api_client.post(LIST_URL, data=data, format="json")

        assert resp.status_code == status.HTTP_201_CREATED
        template = E2BSandboxTemplate.objects.get(template_id="e2b-envd")
        assert (template.is_builtin, template.resource_name, template.prewarm_count) == (True, "e2b-envd", 2)
        sync_task.delay.assert_called_once_with("e2b-envd")
        assert _audited()

    def test_rejects_duplicate(self, plat_mgt_api_client):
        make_builtin_template("e2b-envd")

        resp = plat_mgt_api_client.post(
            LIST_URL, data={"template_id": "e2b-envd", "name": "x", "image": IMAGE}, format="json"
        )

        assert resp.status_code == status.HTTP_409_CONFLICT

    def test_rejects_double_dash(self, plat_mgt_api_client):
        """双横线留给自定义模板的应用前缀"""
        resp = plat_mgt_api_client.post(
            LIST_URL, data={"template_id": "app--tpl", "name": "x", "image": IMAGE}, format="json"
        )

        assert resp.status_code == status.HTTP_400_BAD_REQUEST


class TestUpdate:
    def test_full_update(self, plat_mgt_api_client):
        template = make_builtin_template("e2b-envd", is_public=True, prewarm_count=2)

        resp = plat_mgt_api_client.put(
            _detail_url("e2b-envd"), data={"name": "Base", "image": "new:v2", "memory_mb": 8192}, format="json"
        )

        assert resp.status_code == status.HTTP_200_OK
        template.refresh_from_db()
        assert (template.image, template.memory_mb) == ("new:v2", 8192)
        # 全量覆盖，没传的回到默认值
        assert (template.prewarm_count, template.is_public, template.enabled) == (0, False, True)
        assert _audited()


class TestDestroy:
    def test_deletes(self, plat_mgt_api_client, sync_task, django_capture_on_commit_callbacks):
        make_builtin_template("e2b-envd")

        with django_capture_on_commit_callbacks(execute=True):
            resp = plat_mgt_api_client.delete(_detail_url("e2b-envd"))

        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not E2BSandboxTemplate.objects.exists()
        sync_task.delay.assert_called_once_with("e2b-envd")

    def test_refuses_while_in_use(self, plat_mgt_api_client, bk_app):
        make_builtin_template("e2b-envd")
        E2BSandbox.objects.create(sandbox_id="sb-1", application=bk_app, cluster_name="c", template_id="e2b-envd")

        resp = plat_mgt_api_client.delete(_detail_url("e2b-envd"))

        assert resp.status_code == status.HTTP_409_CONFLICT
        assert E2BSandboxTemplate.objects.exists()


class TestSync:
    def test_returns_per_cluster_results(self, plat_mgt_api_client):
        results = [
            ClusterSyncResult(cluster_name="c1", synced=["e2b-envd"], failed={"bad": "boom"}, pruned=["old"]),
            ClusterSyncResult(cluster_name="c2", error="unreachable"),
        ]

        with mock.patch("paasng.plat_mgt.agent_sandbox.views.sync_all", return_value=results):
            resp = plat_mgt_api_client.post(SYNC_URL)

        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == [
            {"cluster_name": "c1", "synced": ["e2b-envd"], "failed": {"bad": "boom"}, "pruned": ["old"], "error": ""},
            {"cluster_name": "c2", "synced": [], "failed": {}, "pruned": [], "error": "unreachable"},
        ]
        assert _audited()


class TestSyncOverview:
    """测试集群 CLUSTER_NAME_FOR_TESTING 分配给默认租户，另一个集群启用了 e2b 但不在分配策略里"""

    @pytest.fixture(autouse=True)
    def e2b_clusters(self):
        for name in (CLUSTER_NAME_FOR_TESTING, OTHER_CLUSTER):
            cluster = Cluster.objects.filter(name=name).first() or G(Cluster, name=name, tenant_id=DEFAULT_TENANT_ID)
            ClusterE2BConfig.objects.create(
                cluster=cluster,
                control_plane_url="http://e2b-gateway:8080",
                data_plane_address="e2b.example.com",
                api_key="key",
                tenant_id=DEFAULT_TENANT_ID,
            )

    @pytest.fixture()
    def templates(self, bk_app):
        """done 全部成功；mine 只需下发到测试集群且待同步；bad 其中一个集群失败；fresh 还没有任何记录"""
        done = make_builtin_template("done")
        _record(done, CLUSTER_NAME_FOR_TESTING, E2BTemplateSyncStatus.SUCCEEDED)
        _record(done, OTHER_CLUSTER, E2BTemplateSyncStatus.SUCCEEDED)
        # 已停用 e2b 的集群留下的记录不算数
        _record(done, "retired-cluster", E2BTemplateSyncStatus.FAILED)

        mine = make_custom_template(bk_app, "mine")
        _record(mine, CLUSTER_NAME_FOR_TESTING, E2BTemplateSyncStatus.PENDING)

        bad = make_builtin_template("bad")
        _record(bad, CLUSTER_NAME_FOR_TESTING, E2BTemplateSyncStatus.SUCCEEDED)
        _record(bad, OTHER_CLUSTER, E2BTemplateSyncStatus.FAILED, "boom")

        make_builtin_template("fresh")
        return {"mine": mine}

    def test_templates(self, plat_mgt_api_client, bk_app, templates):
        resp = plat_mgt_api_client.get(SYNC_TEMPLATES_URL)

        assert resp.status_code == status.HTTP_200_OK
        items = {i["resource_name"]: i for i in resp.json()}
        mine = templates["mine"].resource_name
        assert {k: v["status"] for k, v in items.items()} == {
            "done": "succeeded",
            mine: "pending",
            "bad": "failed",
            "fresh": "pending",
        }
        assert {r["cluster_name"] for r in items["done"]["records"]} == {CLUSTER_NAME_FOR_TESTING, OTHER_CLUSTER}
        assert items[mine]["app_code"] == bk_app.code
        assert items[mine]["missing"] == []
        assert items["fresh"]["missing"] == sorted([CLUSTER_NAME_FOR_TESTING, OTHER_CLUSTER])

    @pytest.mark.parametrize(
        ("query", "expected"),
        [
            ({"status": "failed"}, ["bad"]),
            ({"is_builtin": "false"}, ["mine"]),
            ({"is_builtin": "true", "status": "pending"}, ["fresh"]),
        ],
    )
    def test_templates_filter(self, plat_mgt_api_client, templates, query, expected):
        resp = plat_mgt_api_client.get(SYNC_TEMPLATES_URL, data=query)

        assert sorted(i["template_id"] for i in resp.json()) == expected

    def test_clusters(self, plat_mgt_api_client, templates):
        resp = plat_mgt_api_client.get(SYNC_CLUSTERS_URL)

        assert resp.status_code == status.HTTP_200_OK
        items = {i["cluster_name"]: i for i in resp.json()}
        assert set(items) == {CLUSTER_NAME_FOR_TESTING, OTHER_CLUSTER}
        main = items[CLUSTER_NAME_FOR_TESTING]
        assert sorted(main["succeeded"]) == ["bad", "done"]
        assert main["pending"] == [templates["mine"].resource_name]
        assert main["missing"] == ["fresh"]
        assert main["completed"] is False
        other = items[OTHER_CLUSTER]
        assert other["failed"] == {"bad": "boom"}
        assert other["missing"] == ["fresh"]

    def test_cluster_completed(self, plat_mgt_api_client):
        template = make_builtin_template("done")
        for name in (CLUSTER_NAME_FOR_TESTING, OTHER_CLUSTER):
            _record(template, name, E2BTemplateSyncStatus.SUCCEEDED)

        resp = plat_mgt_api_client.get(SYNC_CLUSTERS_URL)

        assert all(i["completed"] for i in resp.json())


def _record(template, cluster_name: str, sync_status: E2BTemplateSyncStatus, message: str = ""):
    E2BSandboxTemplateSyncRecord.objects.create(
        template=template, cluster_name=cluster_name, status=sync_status.value, message=message
    )


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("get", LIST_URL),
        ("post", LIST_URL),
        ("delete", _detail_url("e2b-envd")),
        ("post", SYNC_URL),
        ("get", SYNC_TEMPLATES_URL),
        ("get", SYNC_CLUSTERS_URL),
    ],
)
def test_requires_plat_manager(api_client, method, url):
    assert getattr(api_client, method)(url).status_code == status.HTTP_403_FORBIDDEN
