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

"""Creating a Project and listing the ones the caller owns."""

from __future__ import annotations

from datetime import UTC, datetime
from http import HTTPStatus

import pytest

from app_spark_api.agent.conversations.models import ConversationNumber
from app_spark_api.core.projects import services
from app_spark_api.core.projects.models import Project
from app_spark_api.core.tenant.user import get_tenant
from tests.helpers import create_user

pytestmark = pytest.mark.django_db(transaction=True)

PROJECTS_URL = "/api/projects/"


async def make_project(*, project_id: str, name: str, owner, tenant_id: str, is_deleted: bool = False) -> Project:
    """Store a Project directly, bypassing the API under test.

    Async because these tests are: the sync ORM refuses to run inside a running event loop, and
    ``acreate`` hands the insert (signals included) to a worker thread where it is allowed.

    ``tenant_id`` is spelled out at every call site rather than defaulted: the API scopes by
    ``get_tenant()``, which is ``default`` while multi-tenant mode is off, whereas the shared
    ``bk_user`` fixture carries a random tenant of its own. Getting that wrong makes a Project
    the API simply cannot see, which reads as a bug in the API rather than in the fixture.
    """
    return await Project.objects.acreate(
        id=project_id,
        name=name,
        creator=owner,
        owner=owner,
        tenant_id=tenant_id,
        is_deleted=is_deleted,
    )


async def create_via_api(client, *, project_id: str, name: str):
    return await client.post(
        PROJECTS_URL,
        data={"id": project_id, "name": name},
        content_type="application/json",
    )


# --- creating ---------------------------------------------------------------------------


async def test_creating_a_project_records_the_caller_as_its_owner(aapi_client, bk_user):
    response = await create_via_api(aapi_client, project_id="spark-demo", name="Spark Demo")

    assert response.status_code == HTTPStatus.CREATED
    body = response.json()
    assert body["id"] == "spark-demo"
    assert body["name"] == "Spark Demo"

    project = await Project.objects.aget(pk="spark-demo")
    assert project.owner == bk_user.pk
    assert project.creator == bk_user.pk
    assert project.tenant_id == get_tenant(bk_user).id


async def test_a_project_created_through_the_api_can_open_a_conversation_at_once(aapi_client):
    """The counter row is derived by a signal, so creating must not be able to skip it."""
    await create_via_api(aapi_client, project_id="spark-demo", name="Spark Demo")

    assert await ConversationNumber.objects.filter(project_id="spark-demo").aexists()


async def test_a_taken_project_id_is_refused_even_from_another_tenant(aapi_client, bk_user):
    """Project ids are global, unlike names: they are the primary key and a directory name."""
    await make_project(project_id="spark-demo", name="Elsewhere", owner=bk_user, tenant_id="some-other-tenant")

    response = await create_via_api(aapi_client, project_id="spark-demo", name="Spark Demo")

    assert response.status_code == HTTPStatus.CONFLICT
    assert "spark-demo" in response.json()["detail"]


async def test_a_name_already_used_in_the_tenant_is_refused(aapi_client, bk_user):
    await make_project(
        project_id="taken-name",
        name="Spark Demo",
        owner=bk_user,
        tenant_id=get_tenant(bk_user).id,
    )

    response = await create_via_api(aapi_client, project_id="spark-demo", name="Spark Demo")

    assert response.status_code == HTTPStatus.CONFLICT
    assert "Spark Demo" in response.json()["detail"]


async def test_a_soft_deleted_project_still_holds_on_to_its_id(aapi_client, bk_user):
    """Why the check runs through ``default_objects``.

    A soft-deleted row still occupies the primary key, so the database will refuse the insert.
    Checking through ``objects``, which hides it, would report no conflict at all and leave the
    raw IntegrityError as the only thing the caller ever sees.
    """
    await make_project(
        project_id="spark-demo",
        name="Deleted Demo",
        owner=bk_user,
        tenant_id=get_tenant(bk_user).id,
        is_deleted=True,
    )

    response = await create_via_api(aapi_client, project_id="spark-demo", name="Spark Demo")

    assert response.status_code == HTTPStatus.CONFLICT


async def test_a_name_taken_after_the_check_is_still_reported_as_a_conflict(aapi_client, bk_user, monkeypatch):
    """The window the up-front check cannot close, and why the insert still guards it.

    Checking first only narrows the race, it does not remove it: two callers can both pass the
    check and then both insert. Here the loser is simulated by having someone else's row appear
    after the check has already passed. It has to come out as a 409 like any other duplicate --
    the alternative is the unique constraint surfacing as a 500 for a request that is merely
    unlucky rather than wrong.
    """
    real_insert = services._insert
    tenant_id = get_tenant(bk_user).id

    def insert_after_losing_the_race(**kwargs):
        # Runs on the worker thread `create_project` hands `_insert` to, so the sync ORM is
        # allowed here -- and the row is committed before the real insert is attempted, which
        # is exactly the state the winner of a race would have left behind.
        Project.objects.create(
            id="faster-caller",
            name="Spark Demo",
            creator=bk_user.pk,
            owner=bk_user.pk,
            tenant_id=tenant_id,
        )
        return real_insert(**kwargs)

    monkeypatch.setattr(services, "_insert", insert_after_losing_the_race)

    response = await create_via_api(aapi_client, project_id="spark-demo", name="Spark Demo")

    assert response.status_code == HTTPStatus.CONFLICT
    assert "Spark Demo" in response.json()["detail"]


@pytest.mark.parametrize(
    "project_id",
    [
        # The reason the pattern is this strict: the id is used as a path component, so
        # anything that can name a parent directory has to be unrepresentable.
        "../etc",
        "a/b",
        "a.b",
        "Spark",  # uppercase
        "9lives",  # must not start with a digit
        "-spark",  # nor with a hyphen
        "a",  # too short
        "a" * 21,  # longer than Project.id can hold
        "spark demo",
        "spark_demo",
        "",
    ],
)
async def test_an_id_that_is_not_safe_as_a_path_component_is_refused(aapi_client, project_id):
    response = await create_via_api(aapi_client, project_id=project_id, name="Spark Demo")

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert not await Project.default_objects.aexists()


async def test_a_name_longer_than_the_column_is_refused_rather_than_truncated(aapi_client):
    response = await create_via_api(aapi_client, project_id="spark-demo", name="x" * 21)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


# --- listing ----------------------------------------------------------------------------


async def test_the_list_shows_only_the_projects_the_caller_owns(aapi_client, bk_user):
    """There is no permission model yet, so "available" can only mean "mine"."""
    tenant_id = get_tenant(bk_user).id
    await make_project(project_id="mine", name="Mine", owner=bk_user, tenant_id=tenant_id)
    await make_project(project_id="theirs", name="Theirs", owner=create_user(), tenant_id=tenant_id)

    body = (await aapi_client.get(PROJECTS_URL)).json()

    assert [item["id"] for item in body["items"]] == ["mine"]
    assert body["count"] == 1


async def test_the_list_hides_soft_deleted_projects(aapi_client, bk_user):
    tenant_id = get_tenant(bk_user).id
    await make_project(project_id="alive", name="Alive", owner=bk_user, tenant_id=tenant_id)
    await make_project(project_id="gone", name="Gone", owner=bk_user, tenant_id=tenant_id, is_deleted=True)

    body = (await aapi_client.get(PROJECTS_URL)).json()

    assert [item["id"] for item in body["items"]] == ["alive"]


async def test_the_list_hides_projects_of_another_tenant(aapi_client, bk_user):
    await make_project(project_id="here", name="Here", owner=bk_user, tenant_id=get_tenant(bk_user).id)
    await make_project(project_id="over-there", name="Over There", owner=bk_user, tenant_id="some-other-tenant")

    body = (await aapi_client.get(PROJECTS_URL)).json()

    assert [item["id"] for item in body["items"]] == ["here"]


async def test_the_list_is_newest_first(aapi_client, bk_user):
    tenant_id = get_tenant(bk_user).id
    for index, project_id in enumerate(["oldest", "middle", "newest"]):
        await make_project(project_id=project_id, name=project_id.title(), owner=bk_user, tenant_id=tenant_id)
        # `created` is auto_now_add, so three rows built back to back can share a timestamp.
        # Written explicitly here because this test is about the order, not about how fast the
        # loop ran.
        await Project.objects.filter(pk=project_id).aupdate(created=datetime(2026, 1, index + 1, tzinfo=UTC))

    body = (await aapi_client.get(PROJECTS_URL)).json()

    assert [item["id"] for item in body["items"]] == ["newest", "middle", "oldest"]


async def test_the_list_is_paginated_by_page_number(aapi_client, bk_user):
    tenant_id = get_tenant(bk_user).id
    for index in range(3):
        await make_project(project_id=f"project-{index}", name=f"Project {index}", owner=bk_user, tenant_id=tenant_id)

    body = (await aapi_client.get(f"{PROJECTS_URL}?page=2&page_size=2")).json()

    assert len(body["items"]) == 1
    # The total, not the size of this page -- that is what lets a client know there is a page 2.
    assert body["count"] == 3


@pytest.mark.parametrize("query", ["page=0", "page=-1", "page_size=0"])
async def test_nonsense_paging_parameters_are_refused(aapi_client, query):
    response = await aapi_client.get(f"{PROJECTS_URL}?{query}")

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


async def test_the_list_of_a_user_without_projects_is_empty_rather_than_missing(aapi_client):
    body = (await aapi_client.get(PROJECTS_URL)).json()

    assert body == {"items": [], "count": 0}


# --- authentication ---------------------------------------------------------------------


@pytest.mark.parametrize("method", ["get", "post"])
async def test_an_anonymous_caller_reaches_no_project_endpoint(aanonymous_api_client, method):
    response = await getattr(aanonymous_api_client, method)(PROJECTS_URL)

    assert response.status_code == HTTPStatus.UNAUTHORIZED
