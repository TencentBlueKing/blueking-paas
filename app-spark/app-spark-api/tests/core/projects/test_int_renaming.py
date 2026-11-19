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

"""Automatic naming after a project is created from a prompt: enqueueing and executing it."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from app_spark_api.agent.runtime.exceptions import ModelCredentialMissingError
from app_spark_api.core.projects import int_renaming, tasks
from app_spark_api.core.projects.constants import INT_RENAMING_TIMEOUT, IntRenamingStatus
from app_spark_api.core.projects.models import Project, ProjIntRenaming
from app_spark_api.infras.llm import FakeLLMConfig, LLMCallError, LLMClient

pytestmark = pytest.mark.django_db(transaction=True)

TENANT = "default"
OWNER = "spark-owner"
PROMPT = "做一个番茄钟，能统计每天专注了多久"


async def make_project(*, project_id: str = "p-sparkdemo", name: str | None = None) -> Project:
    return await Project.objects.acreate(
        id=project_id,
        name=name or project_id,
        creator=OWNER,
        owner=OWNER,
        tenant_id=TENANT,
        initial_prompt=PROMPT,
    )


async def make_record(project: Project) -> ProjIntRenaming:
    return await ProjIntRenaming.objects.acreate(project=project)


def fake_llm(name: str | None) -> LLMClient:
    return LLMClient(FakeLLMConfig(output={"name": name}))


class TestRun:
    async def test_completes_with_the_generated_name_and_replaces_the_placeholder(self):
        project = await make_project()
        record = await make_record(project)

        await int_renaming.run(project.pk, llm=fake_llm("番茄专注钟"))

        await record.arefresh_from_db()
        assert record.status == IntRenamingStatus.COMPLETED
        assert record.name == "番茄专注钟"
        assert record.completed_at is not None
        assert record.error_at is None
        stored = await Project.objects.aget(pk=project.pk)
        assert stored.name == "番茄专注钟"

    async def test_completes_without_a_name_and_keeps_the_placeholder(self):
        """The model may decide the prompt is too vague; that is a normal outcome, not a failure."""
        project = await make_project()
        record = await make_record(project)

        await int_renaming.run(project.pk, llm=fake_llm(None))

        await record.arefresh_from_db()
        assert (record.status, record.name) == (IntRenamingStatus.COMPLETED, None)
        assert (await Project.objects.aget(pk=project.pk)).name == project.pk

    async def test_keeps_a_name_the_user_changed_while_the_task_was_running(self):
        project = await make_project()
        await make_record(project)
        renamed = await Project.objects.arename(project.pk, "用户自己起的名字")

        await int_renaming.run(project.pk, llm=fake_llm("番茄专注钟"))

        assert renamed is True
        assert (await Project.objects.aget(pk=project.pk)).name == "用户自己起的名字"

    async def test_records_a_model_failure(self, monkeypatch):
        project = await make_project()
        record = await make_record(project)

        async def fail(*args, **kwargs):
            raise LLMCallError("model refused the request")

        monkeypatch.setattr(int_renaming, "generate_project_name", fail)

        await int_renaming.run(project.pk, llm=fake_llm("never used"))

        await record.arefresh_from_db()
        assert record.status == IntRenamingStatus.FAILED
        assert record.error_msg == "model refused the request"
        assert record.error_at is not None
        assert record.completed_at is None
        assert (await Project.objects.aget(pk=project.pk)).name == project.pk

    async def test_a_finished_record_is_not_named_again(self, monkeypatch):
        project = await make_project()
        record = await make_record(project)
        await record.complete(None)

        async def unexpected(*args, **kwargs):
            raise AssertionError("a finished record must not call the model again")

        monkeypatch.setattr(int_renaming, "generate_project_name", unexpected)

        await int_renaming.run(project.pk, llm=fake_llm("never used"))

        await record.arefresh_from_db()
        assert record.status == IntRenamingStatus.COMPLETED
        assert record.name is None

    async def test_a_record_failed_as_overdue_is_not_completed_by_a_late_task(self):
        project = await make_project()
        record = await make_record(project)
        overdue = timezone.now() - INT_RENAMING_TIMEOUT - timedelta(seconds=1)
        await ProjIntRenaming.objects.filter(pk=record.pk).aupdate(created_at=overdue)
        await record.arefresh_from_db()

        await record.fail_if_overdue()
        await int_renaming.run(project.pk, llm=fake_llm("番茄专注钟"))

        await record.arefresh_from_db()
        assert (record.status, record.error_msg) == (IntRenamingStatus.FAILED, ProjIntRenaming.TIMED_OUT_MESSAGE)
        assert (await Project.objects.aget(pk=project.pk)).name == project.pk

    async def test_a_recent_pending_record_is_not_failed(self):
        project = await make_project()
        record = await make_record(project)

        await record.fail_if_overdue()

        await record.arefresh_from_db()
        assert record.status == IntRenamingStatus.PENDING

    async def test_a_deleted_project_is_skipped(self):
        project = await make_project()
        record = await make_record(project)
        await Project.objects.asoft_delete(project.pk)

        await int_renaming.run(project.pk, llm=fake_llm("番茄专注钟"))

        await record.arefresh_from_db()
        assert record.status == IntRenamingStatus.PENDING


class TestStart:
    async def test_records_the_task_and_enqueues_it(self, settings, monkeypatch):
        settings.LLM_SOURCE = "fake"
        project = await make_project()
        enqueued = []
        monkeypatch.setattr(
            tasks.rename_project_from_prompt,
            "apply_async",
            lambda *, args: enqueued.append(args),
        )

        await tasks.start_int_renaming(project, credential=None)

        assert enqueued == [(project.pk, None)]
        record = await ProjIntRenaming.objects.aget(project_id=project.pk)
        assert record.status == IntRenamingStatus.PENDING

    async def test_a_failure_to_get_a_token_is_recorded_not_raised(self, settings, monkeypatch):
        settings.LLM_SOURCE = "bkaidev"
        project = await make_project()

        async def no_credential(credential):
            raise ModelCredentialMissingError("the request has no login")

        monkeypatch.setattr(tasks, "fetch_bkaidev_access_token", no_credential)
        monkeypatch.setattr(
            tasks.rename_project_from_prompt,
            "apply_async",
            lambda **kwargs: pytest.fail("nothing should be enqueued"),
        )

        await tasks.start_int_renaming(project, credential=None)

        record = await ProjIntRenaming.objects.aget(project_id=project.pk)
        assert record.status == IntRenamingStatus.FAILED
        assert record.error_msg == tasks.START_FAILED_MESSAGE

    async def test_a_failure_to_enqueue_is_recorded_not_raised(self, settings, monkeypatch):
        settings.LLM_SOURCE = "fake"
        project = await make_project()

        def broker_is_down(*, args):
            raise RuntimeError("broker is down")

        monkeypatch.setattr(tasks.rename_project_from_prompt, "apply_async", broker_is_down)

        await tasks.start_int_renaming(project, credential=None)

        record = await ProjIntRenaming.objects.aget(project_id=project.pk)
        assert record.status == IntRenamingStatus.FAILED
        assert record.error_msg == tasks.START_FAILED_MESSAGE

    async def test_starting_twice_keeps_one_record(self, settings, monkeypatch):
        settings.LLM_SOURCE = "fake"
        project = await make_project()
        monkeypatch.setattr(tasks.rename_project_from_prompt, "apply_async", lambda **kwargs: None)

        await tasks.start_int_renaming(project, credential=None)
        await tasks.start_int_renaming(project, credential=None)

        assert await ProjIntRenaming.objects.filter(project_id=project.pk).acount() == 1


def test_the_task_entry_point_builds_the_client_from_settings(settings):
    """The Celery entry point runs the async workflow from a sync worker process."""
    settings.LLM_SOURCE = "fake"
    project = Project.objects.create(
        id="p-syncworker",
        name="p-syncworker",
        creator=OWNER,
        owner=OWNER,
        tenant_id=TENANT,
        initial_prompt=PROMPT,
    )
    ProjIntRenaming.objects.create(project=project)

    tasks.rename_project_from_prompt(project.pk, access_token=None)

    record = ProjIntRenaming.objects.get(project_id=project.pk)
    assert record.status == IntRenamingStatus.COMPLETED
