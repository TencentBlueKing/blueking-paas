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

"""Renaming a Project at the service level: the rules the HTTP tests in tests/api do not reach."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app_spark_api.core.projects import services
from app_spark_api.core.projects.exceptions import ProjectAlreadyDeletedError, ProjectNameTakenError
from app_spark_api.core.projects.models import Project

pytestmark = pytest.mark.django_db(transaction=True)

TENANT = "default"
OWNER = "spark-owner"


async def make_project(*, project_id: str, name: str, tenant_id: str = TENANT) -> Project:
    return await Project.objects.acreate(
        id=project_id,
        name=name,
        creator=OWNER,
        owner=OWNER,
        tenant_id=tenant_id,
    )


async def test_renaming_persists_the_new_name_and_bumps_updated_at():
    project = await make_project(project_id="spark-demo", name="Spark Demo")
    # 固定一个过去的时间点，免得断言依赖两次写入之间的时钟分辨率。
    past = datetime(2026, 1, 1, tzinfo=UTC)
    await Project.objects.filter(pk="spark-demo").aupdate(updated_at=past)
    await project.arefresh_from_db()

    renamed = await services.rename_project(project, name="Spark Renamed")

    assert renamed.name == "Spark Renamed"
    assert renamed.updated_at > past
    stored = await Project.objects.aget(pk="spark-demo")
    assert (stored.name, stored.updated_at) == ("Spark Renamed", renamed.updated_at)


async def test_renaming_to_the_current_name_is_not_a_conflict():
    """A project trivially "holds" its own name; that must not read as someone else taking it."""
    project = await make_project(project_id="spark-demo", name="Spark Demo")
    original_updated_at = project.updated_at

    renamed = await services.rename_project(project, name="Spark Demo")

    assert renamed.name == "Spark Demo"
    stored = await Project.objects.aget(pk="spark-demo")
    assert stored.updated_at == original_updated_at


async def test_names_only_need_to_be_unique_within_a_tenant():
    await make_project(project_id="elsewhere", name="Shared", tenant_id="some-other-tenant")
    project = await make_project(project_id="spark-demo", name="Spark Demo")

    renamed = await services.rename_project(project, name="Shared")

    assert renamed.name == "Shared"


async def test_a_name_released_by_a_deleted_project_can_be_reused():
    await make_project(project_id="deleted-demo", name="Released")
    await Project.objects.asoft_delete("deleted-demo")
    project = await make_project(project_id="spark-demo", name="Spark Demo")

    renamed = await services.rename_project(project, name="Released")

    assert renamed.name == "Released"


async def test_renaming_a_project_deleted_after_it_was_fetched_is_reported_as_deleted():
    """The caller fetched the project, then a concurrent delete won before the update ran."""
    project = await make_project(project_id="spark-demo", name="Spark Demo")
    await Project.objects.asoft_delete("spark-demo")

    with pytest.raises(ProjectAlreadyDeletedError):
        await services.rename_project(project, name="Spark Renamed")

    deleted = await Project.default_objects.aget(pk="spark-demo")
    # 不能把已删除项目的名称写回去，否则它会重新占住租户内的唯一约束。
    assert (deleted.is_deleted, deleted.name) == (True, None)


async def test_a_project_deleted_right_after_the_rename_is_reported_as_deleted(monkeypatch):
    """The update lands, then a concurrent delete wins before the result is read back.

    Returning that row would hand a deleted project (with no name) to the caller.
    """
    project = await make_project(project_id="spark-demo", name="Spark Demo")
    real_arename = Project.objects.arename

    async def arename_then_lose_to_a_delete(project_id, name):
        changed = await real_arename(project_id, name)
        await Project.objects.asoft_delete(project_id)
        return changed

    monkeypatch.setattr(Project.objects, "arename", arename_then_lose_to_a_delete)

    with pytest.raises(ProjectAlreadyDeletedError):
        await services.rename_project(project, name="Spark Renamed")


async def test_a_name_taken_after_the_check_is_still_reported_as_a_conflict(monkeypatch):
    """The up-front check only narrows the race; the unique constraint is what closes it.

    Someone else's row appears after the check has passed. That must still come out as a
    name conflict rather than a raw IntegrityError.
    """
    project = await make_project(project_id="spark-demo", name="Spark Demo")
    real_arename = Project.objects.arename

    async def arename_after_losing_the_race(project_id, name):
        await make_project(project_id="faster-caller", name=name)
        return await real_arename(project_id, name)

    monkeypatch.setattr(Project.objects, "arename", arename_after_losing_the_race)

    with pytest.raises(ProjectNameTakenError):
        await services.rename_project(project, name="Contested")

    assert (await Project.objects.aget(pk="spark-demo")).name == "Spark Demo"
