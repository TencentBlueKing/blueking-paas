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

"""How a conversation gets the number it is addressed by."""

from __future__ import annotations

import threading

import pytest
from django.db import connection

from app_spark_api.agent.conversations.models import Conversation, ConversationNumber
from app_spark_api.core.projects.models import Project

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def project(bk_user) -> Project:
    return Project.objects.create(
        id="numbering",
        name="Numbering",
        creator=bk_user,
        owner=bk_user,
        tenant_id=bk_user.tenant_id,
    )


@pytest.fixture
def other_project(bk_user) -> Project:
    return Project.objects.create(
        id="numbering-too",
        name="Numbering Too",
        creator=bk_user,
        owner=bk_user,
        tenant_id=bk_user.tenant_id,
    )


def test_a_new_project_arrives_with_its_counter_ready(project):
    """What lets the allocation assume the row is there instead of checking every time."""
    assert ConversationNumber.objects.get(project=project).last_number == 0


def test_a_project_built_behind_the_signals_back_is_refused_rather_than_renumbered(project):
    """Silently creating the counter here would restart at 0 and reissue live numbers."""
    Conversation.objects.create_for_project(project, owner=None)
    ConversationNumber.objects.filter(project=project).delete()

    with pytest.raises(ConversationNumber.DoesNotExist):
        Conversation.objects.create_for_project(project, owner=None)


def test_the_first_conversation_of_a_project_is_number_one(project, bk_user):
    conversation = Conversation.objects.create_for_project(project, owner=bk_user.pk)

    assert conversation.number == 1
    assert conversation.project_id == project.pk
    assert conversation.tenant_id == project.tenant_id


def test_each_further_conversation_takes_the_next_number(project, bk_user):
    numbers = [Conversation.objects.create_for_project(project, owner=bk_user.pk).number for _ in range(3)]

    assert numbers == [1, 2, 3]


def test_every_project_counts_from_one_of_its_own(project, other_project, bk_user):
    """The number is only meaningful inside a Project, which is what keeps it small."""
    Conversation.objects.create_for_project(project, owner=bk_user.pk)
    Conversation.objects.create_for_project(project, owner=bk_user.pk)

    first_elsewhere = Conversation.objects.create_for_project(other_project, owner=bk_user.pk)

    assert first_elsewhere.number == 1


def test_a_deleted_conversation_does_not_give_its_number_back(project, bk_user):
    """Reissuing a number would point an already-shared link at a different conversation."""
    Conversation.objects.create_for_project(project, owner=bk_user.pk)
    second = Conversation.objects.create_for_project(project, owner=bk_user.pk)
    second.delete()

    assert Conversation.objects.create_for_project(project, owner=bk_user.pk).number == 3


def test_the_counter_goes_away_with_its_project(project, bk_user):
    Conversation.objects.create_for_project(project, owner=bk_user.pk)

    project.delete()

    assert not ConversationNumber.objects.filter(project_id="numbering").exists()


def test_concurrent_creates_never_hand_out_the_same_number(project, bk_user):
    """The reason the counter is a table of its own, rather than a MAX(number) + 1.

    Every worker is held at a barrier so they all reach the allocation together; with a read
    followed by a write they would read the same value and collide.
    """
    workers = 8
    barrier = threading.Barrier(workers, timeout=30)
    numbers: list[int] = []
    failures: list[BaseException] = []

    def create_one() -> None:
        try:
            barrier.wait()
            numbers.append(Conversation.objects.create_for_project(project, owner=bk_user.pk).number)
        except BaseException as exc:  # noqa: BLE001  -- reported below rather than lost in a thread
            failures.append(exc)
        finally:
            # Each thread got its own connection; leaving them open would exhaust the pool and
            # keep the test database from being torn down.
            connection.close()

    threads = [threading.Thread(target=create_one) for _ in range(workers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert failures == []
    assert sorted(numbers) == list(range(1, workers + 1))
    assert ConversationNumber.objects.get(project=project).last_number == workers
