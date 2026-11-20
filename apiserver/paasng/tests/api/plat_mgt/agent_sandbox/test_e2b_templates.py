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
from paasng.platform.agent_sandbox.e2b.template_sync.manifests import spec_digest
from paasng.platform.agent_sandbox.models import E2BSandbox, E2BSandboxTemplate, E2BSandboxTemplateSyncState
from tests.paasng.platform.agent_sandbox.e2b.test_utils import IMAGE, make_builtin_template, make_custom_template
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
def _mock_sync_task():
    with mock.patch("paasng.platform.agent_sandbox.e2b.templates.sync_e2b_templates_task"):
        yield


@pytest.fixture()
def e2b_clusters():
    for name in (CLUSTER_NAME_FOR_TESTING, OTHER_CLUSTER):
        cluster = Cluster.objects.filter(name=name).first() or G(Cluster, name=name, tenant_id=DEFAULT_TENANT_ID)
        ClusterE2BConfig.objects.create(
            cluster=cluster,
            control_plane_url="http://e2b-gateway:8080",
            data_plane_address="e2b.example.com",
            api_key="key",
            tenant_id=DEFAULT_TENANT_ID,
        )


def _audited() -> bool:
    return AdminOperationRecord.objects.filter(target=OperationTarget.E2B_SANDBOX_TEMPLATE.value).exists()


class TestList:
    def test_lists_builtin_only(self, plat_mgt_api_client, bk_app):
        make_builtin_template("e2b-envd", is_public=False, env_vars={"A": "1"})
        make_custom_template(bk_app, "custom")

        resp = plat_mgt_api_client.get(LIST_URL)

        assert resp.status_code == status.HTTP_200_OK
        (item,) = resp.json()
        assert item["template_id"] == "e2b-envd"
        assert item["env_vars"] == {"A": "1"}
        assert item["is_public"] is False

    def test_custom_template_is_not_reachable(self, plat_mgt_api_client, bk_app):
        make_custom_template(bk_app, "custom")

        assert plat_mgt_api_client.get(_detail_url("custom")).status_code == status.HTTP_404_NOT_FOUND


class TestCreate:
    def test_creates_builtin(self, plat_mgt_api_client):
        data = {"template_id": "e2b-envd", "name": "Base", "image": IMAGE, "prewarm_count": 2, "is_public": True}

        resp = plat_mgt_api_client.post(LIST_URL, data=data, format="json")

        assert resp.status_code == status.HTTP_201_CREATED
        template = E2BSandboxTemplate.objects.get(template_id="e2b-envd")
        assert (template.is_builtin, template.prewarm_count) == (True, 2)
        assert _audited()

    def test_rejects_duplicate(self, plat_mgt_api_client):
        make_builtin_template("e2b-envd")

        resp = plat_mgt_api_client.post(
            LIST_URL, data={"template_id": "e2b-envd", "name": "x", "image": IMAGE}, format="json"
        )

        assert resp.status_code == status.HTTP_409_CONFLICT


class TestUpdate:
    def test_full_update(self, plat_mgt_api_client):
        template = make_builtin_template("e2b-envd", is_public=True, prewarm_count=2)

        resp = plat_mgt_api_client.put(
            _detail_url("e2b-envd"), data={"name": "Base", "image": "new:v2", "memory_mb": 2048}, format="json"
        )

        assert resp.status_code == status.HTTP_200_OK
        template.refresh_from_db()
        assert (template.image, template.memory_mb) == ("new:v2", 2048)
        # 全量覆盖，没传的回到默认值
        assert (template.prewarm_count, template.is_public, template.enabled) == (0, False, True)
        assert _audited()


class TestDestroy:
    def test_deletes(self, plat_mgt_api_client):
        make_builtin_template("e2b-envd")

        resp = plat_mgt_api_client.delete(_detail_url("e2b-envd"))

        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not E2BSandboxTemplate.objects.exists()
        assert _audited()

    def test_refuses_while_in_use(self, plat_mgt_api_client, bk_app):
        make_builtin_template("e2b-envd")
        E2BSandbox.objects.create(sandbox_id="sb-1", application=bk_app, cluster_name="c", template_id="e2b-envd")

        resp = plat_mgt_api_client.delete(_detail_url("e2b-envd"))

        assert resp.status_code == status.HTTP_409_CONFLICT
        assert E2BSandboxTemplate.objects.exists()


@pytest.mark.usefixtures("e2b_clusters")
class TestSync:
    @pytest.mark.parametrize(
        ("data", "scope"),
        [
            ({}, (None, None)),
            ({"cluster_names": [OTHER_CLUSTER], "resource_names": ["e2b-envd"]}, ([OTHER_CLUSTER], ["e2b-envd"])),
        ],
    )
    def test_dispatches_scope(self, plat_mgt_api_client, data, scope):
        make_builtin_template("e2b-envd")
        cluster_names, resource_names = scope

        with (
            mock.patch("paasng.plat_mgt.agent_sandbox.views.reset_unsynced_to_pending") as reset_unsynced_to_pending,
            mock.patch("paasng.plat_mgt.agent_sandbox.views.sync_e2b_templates_task") as task,
        ):
            resp = plat_mgt_api_client.post(SYNC_URL, data=data, format="json")

        assert resp.status_code == status.HTTP_202_ACCEPTED
        reset_unsynced_to_pending.assert_called_once_with(
            set(cluster_names) if cluster_names else None, set(resource_names) if resource_names else None
        )
        task.delay.assert_called_once_with(cluster_names=cluster_names, resource_names=resource_names)
        assert _audited()

    @pytest.mark.parametrize(
        "data", [{"cluster_names": ["not-e2b"]}, {"resource_names": ["missing"]}, {"cluster_names": []}]
    )
    def test_rejects_unknown_scope(self, plat_mgt_api_client, data):
        """拼错名字时报错，而不是静默什么都不同步"""
        with mock.patch("paasng.plat_mgt.agent_sandbox.views.sync_e2b_templates_task") as task:
            resp = plat_mgt_api_client.post(SYNC_URL, data=data, format="json")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        task.delay.assert_not_called()


@pytest.mark.usefixtures("e2b_clusters")
class TestSyncOverview:
    """测试集群 CLUSTER_NAME_FOR_TESTING 分配给默认租户"""

    @pytest.fixture()
    def templates(self, bk_app) -> dict[str, E2BSandboxTemplate]:
        """准备各下发状态的模板，按模板标识返回，供用例按标识取用。

        - done：内置模板，所有集群都下发成功
        - custom：自定义模板，只需下发到测试集群，当前待同步
        - fresh：内置模板，还没有任何下发状态
        """
        done = make_builtin_template("done")
        for name in (CLUSTER_NAME_FOR_TESTING, OTHER_CLUSTER):
            E2BSandboxTemplateSyncState.objects.create(
                template=done,
                cluster_name=name,
                status=E2BTemplateSyncStatus.SUCCEEDED.value,
                digest=spec_digest(done),
            )
        custom = make_custom_template(bk_app, "custom")
        E2BSandboxTemplateSyncState.objects.create(
            template=custom, cluster_name=CLUSTER_NAME_FOR_TESTING, status=E2BTemplateSyncStatus.PENDING.value
        )
        fresh = make_builtin_template("fresh")
        return {"done": done, "custom": custom, "fresh": fresh}

    def test_templates(self, plat_mgt_api_client, bk_app, templates):
        resp = plat_mgt_api_client.get(SYNC_TEMPLATES_URL)

        assert resp.status_code == status.HTTP_200_OK
        items = {i["template_id"]: i for i in resp.json()}
        assert {k: (v["status"], v["is_builtin"], v["app_code"]) for k, v in items.items()} == {
            "done": ("succeeded", True, None),
            "custom": ("pending", False, bk_app.code),
            "fresh": ("pending", True, None),
        }
        assert items["custom"]["resource_name"] == templates["custom"].resource_name
        (state,) = items["custom"]["states"]
        assert (state["cluster_name"], state["status"], state["up_to_date"]) == (
            CLUSTER_NAME_FOR_TESTING,
            "pending",
            False,
        )
        assert items["fresh"]["missing"] == sorted([CLUSTER_NAME_FOR_TESTING, OTHER_CLUSTER])

    @pytest.mark.parametrize(
        ("query", "expected"),
        [
            ({"status": "succeeded"}, ["done"]),
            ({"is_builtin": "false"}, ["custom"]),
            ({"is_builtin": "true", "status": "pending"}, ["fresh"]),
        ],
    )
    @pytest.mark.usefixtures("templates")
    def test_templates_filter(self, plat_mgt_api_client, query, expected):
        resp = plat_mgt_api_client.get(SYNC_TEMPLATES_URL, data=query)

        assert sorted(i["template_id"] for i in resp.json()) == expected

    def test_clusters(self, plat_mgt_api_client, templates):
        resp = plat_mgt_api_client.get(SYNC_CLUSTERS_URL)

        assert resp.status_code == status.HTTP_200_OK
        items = {i["cluster_name"]: i for i in resp.json()}
        assert set(items) == {CLUSTER_NAME_FOR_TESTING, OTHER_CLUSTER}
        main = items[CLUSTER_NAME_FOR_TESTING]
        assert (main["succeeded"], main["pending"], main["failed"], main["missing"], main["completed"]) == (
            ["done"],
            [templates["custom"].resource_name],
            {},
            ["fresh"],
            False,
        )
        assert main["namespace"]


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
