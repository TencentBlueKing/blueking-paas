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

"""The owner reads the publication state, starts a deployment and clears its result; nobody else can."""

from http import HTTPStatus

import pytest
from django.utils import timezone

from app_spark_api.core.projects.models import Project
from app_spark_api.core.tenant.user import get_tenant
from app_spark_api.infras.bk_paas import BkPaaSApiError, BkPaaSClient
from app_spark_api.publication.models import DevCenterAppBinding, PublicationTask
from app_spark_api.publication.packaging import PackagedSource
from tests.helpers import create_user
from tests.publication.fake import FakeBkPaaSClient

pytestmark = pytest.mark.django_db(transaction=True)

PROJECT_ID = "spark-demo"
URL = f"/api/projects/{PROJECT_ID}/publication/"


@pytest.fixture(autouse=True)
def packager(monkeypatch, settings) -> None:
    """Know versions v1 and v2 and pack them instantly, and give the developer center a console address."""
    settings.BKPAAS_URL = "https://bkpaas.example.com"

    async def version_exists(project, version_id):
        return version_id in ("v1", "v2")

    async def package_version(project, version_id):
        return PackagedSource(f"{version_id}-abc1234", f"https://bkrepo.example.com/{version_id}")

    monkeypatch.setattr("app_spark_api.publication.packaging.aversion_exists", version_exists)
    monkeypatch.setattr("app_spark_api.publication.packaging.apackage_version", package_version)


@pytest.fixture(autouse=True)
def dev_center(monkeypatch) -> FakeBkPaaSClient:
    """Answer the developer center calls made within the request, and keep polls off RabbitMQ."""
    fake = FakeBkPaaSClient()
    monkeypatch.setattr(BkPaaSClient, "from_settings", lambda: fake)
    monkeypatch.setattr("app_spark_api.publication.tasks.schedule_deployment_prepare", lambda *args: None)
    return fake


@pytest.fixture()
async def owned_project(bk_user) -> Project:
    """A Project the logged-in user owns, in the tenant the API scopes to."""
    return await Project.objects.acreate(
        id=PROJECT_ID, name="Spark Demo", creator=bk_user, owner=bk_user, tenant_id=get_tenant(bk_user).id
    )


async def post_deployment(client, version_id: str = "v2", **extra):
    return await client.post(
        f"{URL}deployments/", data={"version_id": version_id, **extra}, content_type="application/json"
    )


async def test_an_unpublished_project_has_nothing_to_show(aapi_client, owned_project):
    response = await aapi_client.get(URL)

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "online": None,
        "task": None,
        "last_failure": None,
        "unseen_result": None,
        "app_code": None,
        # 唯一名称还是项目 ID 时，预填项目名称。
        "default_app_name": "SparkDemo",
        "dev_center_links": None,
    }


async def test_deploying_creates_the_app_and_leaves_packing_to_celery(aapi_client, owned_project, bk_user, dev_center):
    response = await post_deployment(aapi_client)

    # 返回时只建好了应用，打包、部署交给 Celery。没指定时应用 ID、名称取项目的。
    assert response.status_code == HTTPStatus.ACCEPTED
    assert response.json()["task"]["stage"] == "packaging"
    (create,) = dev_center.called("create_app")
    assert (create["code"], create["name"], create["operator"]) == ("spark-demo", "SparkDemo", bk_user.username)


async def test_a_bound_project_ignores_the_app_code_and_name(aapi_client, owned_project):
    await DevCenterAppBinding.objects.acreate(project=owned_project, app_code="sparkdemo-a1b2", module_name="default")

    response = await post_deployment(aapi_client, app_name="!!!")

    assert response.status_code == HTTPStatus.ACCEPTED
    assert (response.json()["app_code"], response.json()["default_app_name"]) == ("sparkdemo-a1b2", None)


async def test_an_app_name_held_by_another_project_is_reported(aapi_client, owned_project, bk_user, dev_center):
    await Project.objects.acreate(
        id="other", name="Other", uniq_name="Spark", creator=bk_user, owner=bk_user, tenant_id=owned_project.tenant_id
    )

    # 按开发者中心的规则过滤后再查，并告诉前端实际会用的名称。
    available = (await aapi_client.get(f"{URL}app-name-availability/", {"name": "Spa rk"})).json()
    response = await post_deployment(aapi_client, app_name="Spark")

    assert available == {"name": "Spark", "available": False}
    assert (response.status_code, response.json()["code"]) == (HTTPStatus.BAD_REQUEST, "PUBLICATION_APP_NAME_TAKEN")
    assert dev_center.calls == []
    # 项目自己的唯一名称不算被占用。
    own = (await aapi_client.get(f"{URL}app-name-availability/", {"name": PROJECT_ID})).json()
    assert own == {"name": PROJECT_ID, "available": True}


@pytest.mark.parametrize(
    ("version_id", "status", "code"),
    [
        ("v9", HTTPStatus.BAD_REQUEST, "PUBLICATION_VERSION_NOT_FOUND"),
        ("v1", HTTPStatus.CONFLICT, "PUBLICATION_TASK_IN_PROGRESS"),
    ],
)
async def test_a_deployment_that_cannot_start_leaves_the_first_task_alone(
    aapi_client, owned_project, version_id, status, code
):
    assert (await post_deployment(aapi_client, "v2")).status_code == HTTPStatus.ACCEPTED

    response = await post_deployment(aapi_client, version_id)

    assert (response.status_code, response.json()["code"]) == (status, code)
    assert [t.version_id async for t in PublicationTask.objects.filter(project=owned_project)] == ["v2"]


async def test_a_failed_submission_answers_with_the_reason(aapi_client, owned_project, dev_center):
    dev_center.queue("create_app", BkPaaSApiError(400, "应用 ID 已存在", fields_detail={"code": ["已存在"]}))

    response = await post_deployment(aapi_client)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {"code": "PUBLICATION_SUBMIT_FAILED", "detail": "应用 ID 已存在"}
    assert (await aapi_client.get(URL)).json()["task"] is None


async def make_finished_task(project, status: str, **fields) -> PublicationTask:
    return await PublicationTask.objects.acreate(
        project=project,
        kind="deployment",
        operator="alice",
        stage="deploying",
        status=status,
        finished_at=timezone.now(),
        **fields,
    )


async def test_deleting_the_unseen_result_clears_it(aapi_client, owned_project):
    await make_finished_task(owned_project, "failed", version_id="v2", error="Procfile error")

    response = await aapi_client.delete(f"{URL}unseen-result/")

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert (await aapi_client.get(URL)).json()["unseen_result"] is None


async def test_a_published_project_shows_its_url_failure_and_dev_center_links(aapi_client, owned_project):
    await DevCenterAppBinding.objects.acreate(project=owned_project, app_code="sparkdemo-a1b2", module_name="default")
    await make_finished_task(
        owned_project, "successful", version_id="v2", access_url="https://apps.example.com/sparkdemo-a1b2/"
    )
    await make_finished_task(owned_project, "failed", version_id="v3", is_update=True, error="Procfile error")

    body = (await aapi_client.get(URL)).json()

    assert (body["online"]["version_id"], body["online"]["url"]) == ("v2", "https://apps.example.com/sparkdemo-a1b2/")
    assert body["last_failure"]["error"] == "Procfile error"
    assert body["dev_center_links"]["deployments"] == (
        "https://bkpaas.example.com/developer-center/apps/sparkdemo-a1b2/deployments/prod"
    )


@pytest.mark.parametrize(("method", "suffix"), [("get", ""), ("post", "deployments/"), ("delete", "unseen-result/")])
async def test_someone_elses_project_is_not_found(aapi_client, method, suffix):
    stranger = create_user()
    await Project.objects.acreate(
        id=PROJECT_ID, name="Spark Demo", creator=stranger, owner=stranger, tenant_id=get_tenant(stranger).id
    )

    response = await getattr(aapi_client, method)(
        f"{URL}{suffix}", data={"version_id": "v2"}, content_type="application/json"
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert not await PublicationTask.objects.aexists()
