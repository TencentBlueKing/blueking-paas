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

"""Creating, listing, renaming and deleting the Projects the caller owns."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from http import HTTPStatus

import pytest
from django.utils import timezone

from app_spark_api.agent.conversations.models import Conversation, ConversationNumber
from app_spark_api.agent.runtime.exceptions import AgentResourceDeletionError
from app_spark_api.core.projects import constants, services
from app_spark_api.core.projects.models import Project
from app_spark_api.core.tenant.user import get_tenant
from tests.helpers import create_user

pytestmark = pytest.mark.django_db(transaction=True)

PROJECTS_URL = "/api/projects/"


async def make_project(
    *, project_id: str, name: str | None, owner, tenant_id: str, is_deleted: bool = False
) -> Project:
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


async def rename_via_api(client, project_id: str, *, name: str):
    return await client.post(
        f"{PROJECTS_URL}{project_id}/rename/",
        data={"name": name},
        content_type="application/json",
    )


async def delete_via_api(client, project_id: str):
    return await client.delete(f"{PROJECTS_URL}{project_id}/")


class RecordingDeletionProvider:
    """Record Project cleanup calls and optionally fail with a public deletion category."""

    def __init__(self):
        self.calls: list[tuple[str, list[str]]] = []
        self.live_counts: list[int] = []
        self.failure_category: str | None = None

    async def delete_project_resources(self, project_id: str, conversation_ids: list[str]) -> None:
        self.calls.append((project_id, conversation_ids))
        # Runtime 被停时会话必须已经结束，否则停完之后还能被新的一轮重新拉起来。
        self.live_counts.append(
            await Conversation.objects.get_queryset().filter(project_id=project_id).live().acount()
        )
        if self.failure_category is not None:
            raise AgentResourceDeletionError(self.failure_category)


@pytest.fixture()
def deletion_provider(monkeypatch):
    provider = RecordingDeletionProvider()

    def get_provider():
        return provider

    monkeypatch.setattr(services, "get_agent_runtime_provider", get_provider)
    return provider


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
    assert response.json()["code"] == "PROJECT_ID_TAKEN"
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
    assert response.json()["code"] == "PROJECT_NAME_TAKEN"
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


async def test_a_soft_deleted_project_releases_its_name(aapi_client, bk_user):
    tenant_id = get_tenant(bk_user).id
    await make_project(
        project_id="deleted-demo",
        name="Spark Demo",
        owner=bk_user,
        tenant_id=tenant_id,
    )
    await Project.objects.asoft_delete("deleted-demo")

    response = await create_via_api(aapi_client, project_id="spark-demo", name="Spark Demo")

    assert response.status_code == HTTPStatus.CREATED


async def test_a_tenant_can_keep_multiple_soft_deleted_projects_without_names(bk_user):
    tenant_id = get_tenant(bk_user).id

    await make_project(project_id="deleted-one", name=None, owner=bk_user, tenant_id=tenant_id, is_deleted=True)
    await make_project(project_id="deleted-two", name=None, owner=bk_user, tenant_id=tenant_id, is_deleted=True)

    assert await Project.default_objects.filter(tenant_id=tenant_id, is_deleted=True, name=None).acount() == 2


async def test_soft_delete_releases_name_only_once(bk_user):
    tenant_id = get_tenant(bk_user).id
    await make_project(project_id="spark-demo", name="Spark Demo", owner=bk_user, tenant_id=tenant_id)

    assert await Project.objects.asoft_delete("spark-demo") is True
    assert await Project.objects.asoft_delete("spark-demo") is False

    deleted = await Project.default_objects.aget(pk="spark-demo")
    assert deleted.is_deleted is True
    assert deleted.name is None
    # 第二次调用没有改到行，所以记下的仍是第一次删除前的名称，而不是被置空后的 NULL。
    assert deleted.name_at_deletion == "Spark Demo"


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
    assert response.json()["code"] == "PROJECT_NAME_TAKEN"
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
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert not await Project.default_objects.aexists()


async def test_a_name_longer_than_the_column_is_refused_rather_than_truncated(aapi_client):
    response = await create_via_api(aapi_client, project_id="spark-demo", name="x" * 21)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.json()["code"] == "VALIDATION_ERROR"


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
        # `created_at` is auto_now_add, so three rows built back to back can share a timestamp.
        # Written explicitly here because this test is about the order, not about how fast the
        # loop ran.
        await Project.objects.filter(pk=project_id).aupdate(created_at=datetime(2026, 1, index + 1, tzinfo=UTC))

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
    assert response.json()["code"] == "VALIDATION_ERROR"


async def test_the_list_of_a_user_without_projects_is_empty_rather_than_missing(aapi_client):
    body = (await aapi_client.get(PROJECTS_URL)).json()

    assert body == {"items": [], "count": 0}


# --- renaming ---------------------------------------------------------------------------
# 规则本身（冲突、并发、名称释放）在 tests/core/projects/test_services.py 里测，这里只覆盖 HTTP 映射。


async def test_renaming_a_project_returns_it_with_the_new_name(aapi_client, bk_user):
    await make_project(project_id="spark-demo", name="Spark Demo", owner=bk_user, tenant_id=get_tenant(bk_user).id)

    response = await rename_via_api(aapi_client, "spark-demo", name="Spark Renamed")

    assert response.status_code == HTTPStatus.OK
    assert (response.json()["id"], response.json()["name"]) == ("spark-demo", "Spark Renamed")


async def test_renaming_to_a_taken_name_is_a_conflict(aapi_client, bk_user):
    tenant_id = get_tenant(bk_user).id
    await make_project(project_id="other-demo", name="Taken", owner=bk_user, tenant_id=tenant_id)
    await make_project(project_id="spark-demo", name="Spark Demo", owner=bk_user, tenant_id=tenant_id)

    response = await rename_via_api(aapi_client, "spark-demo", name="Taken")

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json()["code"] == "PROJECT_NAME_TAKEN"
    assert "Taken" in response.json()["detail"]
    assert (await Project.objects.aget(pk="spark-demo")).name == "Spark Demo"


async def test_invisible_projects_cannot_be_renamed(aapi_client, bk_user):
    tenant_id = get_tenant(bk_user).id
    await make_project(project_id="deleted-demo", name=None, owner=bk_user, tenant_id=tenant_id, is_deleted=True)
    await make_project(project_id="other-owner", name="Other Owner", owner=create_user(), tenant_id=tenant_id)
    await make_project(project_id="other-tenant", name="Other Tenant", owner=bk_user, tenant_id="some-other-tenant")

    responses = [
        await rename_via_api(aapi_client, project_id, name="Hijacked")
        for project_id in ("missing-demo", "deleted-demo", "other-owner", "other-tenant")
    ]

    assert {response.status_code for response in responses} == {HTTPStatus.NOT_FOUND}
    assert {response.json()["code"] for response in responses} == {"RESOURCE_NOT_FOUND"}
    assert not await Project.default_objects.filter(name="Hijacked").aexists()


async def test_a_project_deleted_during_the_rename_is_not_found(aapi_client, bk_user, monkeypatch):
    """A concurrent delete must look like any other invisible project, not a 500."""
    await make_project(project_id="spark-demo", name="Spark Demo", owner=bk_user, tenant_id=get_tenant(bk_user).id)
    real_arename = Project.objects.arename

    async def arename_then_lose_to_a_delete(project_id, name):
        changed = await real_arename(project_id, name)
        await Project.objects.asoft_delete(project_id)
        return changed

    monkeypatch.setattr(Project.objects, "arename", arename_then_lose_to_a_delete)

    response = await rename_via_api(aapi_client, "spark-demo", name="Spark Renamed")

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {"code": "RESOURCE_NOT_FOUND", "detail": "Resource not found."}


@pytest.mark.parametrize("name", ["", "x" * 21])
async def test_a_new_name_outside_the_column_limits_is_refused(aapi_client, bk_user, name):
    await make_project(project_id="spark-demo", name="Spark Demo", owner=bk_user, tenant_id=get_tenant(bk_user).id)

    response = await rename_via_api(aapi_client, "spark-demo", name=name)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.json()["code"] == "VALIDATION_ERROR"


async def test_an_anonymous_caller_cannot_rename_a_project(aanonymous_api_client):
    response = await rename_via_api(aanonymous_api_client, "spark-demo", name="Spark Renamed")

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()["code"] == "AUTHENTICATION_REQUIRED"


# --- deleting ---------------------------------------------------------------------------


async def test_deleting_a_project_finishes_cleanup_before_releasing_its_name(aapi_client, bk_user, deletion_provider):
    tenant_id = get_tenant(bk_user).id
    await make_project(project_id="spark-demo", name="Spark Demo", owner=bk_user, tenant_id=tenant_id)
    counter = await ConversationNumber.objects.aget(project_id="spark-demo")
    original_number = counter.last_number

    response = await delete_via_api(aapi_client, "spark-demo")

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert response.content == b""
    assert deletion_provider.calls == [("spark-demo", [])]
    deleted = await Project.default_objects.aget(pk="spark-demo")
    assert (deleted.is_deleted, deleted.name, deleted.name_at_deletion) == (True, None, "Spark Demo")
    counter = await ConversationNumber.objects.aget(project_id="spark-demo")
    assert counter.last_number == original_number

    reused = await create_via_api(aapi_client, project_id="new-demo", name="Spark Demo")
    blocked = await create_via_api(aapi_client, project_id="spark-demo", name="Another Demo")
    assert reused.status_code == HTTPStatus.CREATED
    assert (blocked.status_code, blocked.json()["code"]) == (HTTPStatus.CONFLICT, "PROJECT_ID_TAKEN")


async def test_deleting_a_project_closes_live_conversations_before_stopping_runtimes(
    aapi_client, bk_user, deletion_provider
):
    tenant_id = get_tenant(bk_user).id
    project = await make_project(
        project_id="spark-demo",
        name="Spark Demo",
        owner=bk_user,
        tenant_id=tenant_id,
    )
    conversation_ids = set()
    for number, closed_at in ((2, None), (3, timezone.now()), (5, None)):
        conversation = await Conversation.objects.acreate(
            project=project,
            number=number,
            owner=bk_user,
            tenant_id=tenant_id,
            closed_at=closed_at,
        )
        conversation_ids.add(str(conversation.id))

    response = await delete_via_api(aapi_client, "spark-demo")

    assert response.status_code == HTTPStatus.NO_CONTENT
    [(project_id, cleaned_ids)] = deletion_provider.calls
    assert (project_id, set(cleaned_ids)) == ("spark-demo", conversation_ids)
    assert deletion_provider.live_counts == [0]
    assert not await Conversation.objects.filter(project=project).aexists()
    assert not await Project.objects.filter(pk="spark-demo").aexists()


async def test_invisible_projects_have_identical_delete_responses(aapi_client, bk_user, deletion_provider):
    tenant_id = get_tenant(bk_user).id
    await make_project(
        project_id="deleted-demo",
        name=None,
        owner=bk_user,
        tenant_id=tenant_id,
        is_deleted=True,
    )
    await make_project(
        project_id="other-owner",
        name="Other Owner Secret",
        owner=create_user(),
        tenant_id=tenant_id,
    )
    await make_project(
        project_id="other-tenant",
        name="Other Tenant Secret",
        owner=bk_user,
        tenant_id="some-other-tenant",
    )

    responses = [
        await delete_via_api(aapi_client, project_id)
        for project_id in ("missing-demo", "deleted-demo", "other-owner", "other-tenant")
    ]

    bodies = [response.json() for response in responses]
    assert {response.status_code for response in responses} == {HTTPStatus.NOT_FOUND}
    assert bodies == [bodies[0]] * 4
    assert bodies[0] == {"code": "RESOURCE_NOT_FOUND", "detail": "Resource not found."}
    assert deletion_provider.calls == []


async def test_an_invalid_project_id_is_rejected_before_deletion(aapi_client, deletion_provider):
    response = await delete_via_api(aapi_client, "Spark")

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert deletion_provider.calls == []


@pytest.mark.parametrize(
    "failure",
    [
        ("close", "conversation"),
        ("runtime", "sandbox"),
        ("runtime", "local process"),
        ("runtime", "local directory"),
        ("conversation", "context file"),
        ("repository", "repository"),
        ("project", "project record"),
    ],
)
async def test_a_deletion_failure_keeps_the_project_visible(
    aapi_client, bk_user, deletion_provider, monkeypatch, failure
):
    stage, category = failure
    await make_project(
        project_id="spark-demo",
        name="Spark Demo",
        owner=bk_user,
        tenant_id=get_tenant(bk_user).id,
    )

    async def fail_cleanup(*_args, **_kwargs):
        raise OSError("sensitive infrastructure detail")

    if stage == "close":
        monkeypatch.setattr(services, "aclose_project_conversations", fail_cleanup)
    elif stage == "runtime":
        deletion_provider.failure_category = category
    elif stage == "conversation":
        monkeypatch.setattr(services, "adelete_project_conversations", fail_cleanup)
    elif stage == "repository":
        monkeypatch.setattr(services, "adelete_project_repository", fail_cleanup)
    else:
        monkeypatch.setattr(Project.objects, "asoft_delete", fail_cleanup)

    response = await delete_via_api(aapi_client, "spark-demo")

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response.json()["code"] == "PROJECT_DELETE_FAILED"
    assert category in response.json()["detail"]
    assert "retry" in response.json()["detail"]
    assert "sensitive infrastructure detail" not in response.json()["detail"]
    project = await Project.objects.aget(pk="spark-demo")
    assert (project.is_deleted, project.name) == (False, "Spark Demo")


async def test_a_timed_out_repository_cleanup_is_retryable(aapi_client, bk_user, deletion_provider, monkeypatch):
    await make_project(
        project_id="spark-demo",
        name="Spark Demo",
        owner=bk_user,
        tenant_id=get_tenant(bk_user).id,
    )

    async def wait_for_repository(_project):
        await asyncio.sleep(60)

    monkeypatch.setattr(services, "adelete_project_repository", wait_for_repository)
    monkeypatch.setattr(constants, "DELETE_PROJECT_TIMEOUT_SECONDS", 0.01)
    started_at = asyncio.get_running_loop().time()

    response = await delete_via_api(aapi_client, "spark-demo")

    assert asyncio.get_running_loop().time() - started_at < 1
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert "repository" in response.json()["detail"]
    project = await Project.objects.aget(pk="spark-demo")
    assert (project.is_deleted, project.name) == (False, "Spark Demo")


async def test_a_failed_deletion_can_be_retried(aapi_client, bk_user, deletion_provider):
    await make_project(
        project_id="spark-demo",
        name="Spark Demo",
        owner=bk_user,
        tenant_id=get_tenant(bk_user).id,
    )
    deletion_provider.failure_category = "sandbox"

    failed = await delete_via_api(aapi_client, "spark-demo")
    deletion_provider.failure_category = None
    succeeded = await delete_via_api(aapi_client, "spark-demo")

    assert failed.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert succeeded.status_code == HTTPStatus.NO_CONTENT
    assert not await Project.objects.filter(pk="spark-demo").aexists()


async def test_concurrent_deletes_do_not_report_a_busy_conflict(aapi_client, bk_user, deletion_provider, monkeypatch):
    await make_project(
        project_id="spark-demo",
        name="Spark Demo",
        owner=bk_user,
        tenant_id=get_tenant(bk_user).id,
    )

    async def complete_cleanup(*_args, **_kwargs):
        await asyncio.sleep(0)

    monkeypatch.setattr(services, "adelete_project_conversations", complete_cleanup)
    monkeypatch.setattr(services, "adelete_project_repository", complete_cleanup)

    responses = await asyncio.gather(
        delete_via_api(aapi_client, "spark-demo"),
        delete_via_api(aapi_client, "spark-demo"),
    )

    assert HTTPStatus.CONFLICT not in {response.status_code for response in responses}
    assert {response.status_code for response in responses}.issubset({HTTPStatus.NO_CONTENT, HTTPStatus.NOT_FOUND})
    assert not await Project.objects.filter(pk="spark-demo").aexists()


async def test_nested_resources_are_hidden_after_project_deletion(aapi_client, bk_user, deletion_provider):
    await make_project(
        project_id="spark-demo",
        name="Spark Demo",
        owner=bk_user,
        tenant_id=get_tenant(bk_user).id,
    )
    assert (await delete_via_api(aapi_client, "spark-demo")).status_code == HTTPStatus.NO_CONTENT

    conversations = await aapi_client.get("/api/projects/spark-demo/conversations/")
    repository = await aapi_client.get("/api/projects/spark-demo/git-repository/")

    assert conversations.status_code == HTTPStatus.NOT_FOUND
    assert repository.status_code == HTTPStatus.NOT_FOUND


# --- authentication ---------------------------------------------------------------------


@pytest.mark.parametrize("method", ["get", "post"])
async def test_an_anonymous_caller_reaches_no_project_endpoint(aanonymous_api_client, method):
    response = await getattr(aanonymous_api_client, method)(PROJECTS_URL)

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()["code"] == "AUTHENTICATION_REQUIRED"


async def test_an_anonymous_caller_cannot_delete_a_project(aanonymous_api_client):
    response = await delete_via_api(aanonymous_api_client, "spark-demo")

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()["code"] == "AUTHENTICATION_REQUIRED"
