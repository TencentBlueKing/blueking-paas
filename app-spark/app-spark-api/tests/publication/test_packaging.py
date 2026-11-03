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

"""A version is a checkpoint tag of the Project; packing it goes through the repository's source packager."""

from types import SimpleNamespace

import pytest

from app_spark_api.agent.conversations.models import Conversation
from app_spark_api.agent.conversations.state_models import ConversationCheckpoint
from app_spark_api.core.projects.models import Project
from app_spark_api.publication.packaging import (
    PACKAGE_URL_EXPIRES_IN,
    SourcePackagingError,
    apackage_version,
    aversion_exists,
)
from app_spark_api.repository.git.exceptions import SourceRefNotFoundError
from app_spark_api.repository.git.models import ProjectGitRepository

pytestmark = pytest.mark.django_db(transaction=True)

TAG = "app-spark/checkpoint/run-1"
COMMIT = "3f2a1bc" + "0" * 33


async def test_only_checkpoints_of_the_project_are_versions(project, bk_user):
    other = await Project.objects.acreate(id="other", name="Other", owner=bk_user.pk, tenant_id=project.tenant_id)
    conversation = await Conversation.objects.acreate(
        project=other, number=1, owner=bk_user, tenant_id=other.tenant_id
    )
    await ConversationCheckpoint.objects.acreate(
        conversation=conversation, run_id="run-1", commit=COMMIT, tag=TAG, context_version=1
    )

    assert await aversion_exists(other, TAG)
    assert not await aversion_exists(project, TAG)


async def test_packing_uploads_the_tag_and_signs_a_short_lived_link(project, monkeypatch):
    await ProjectGitRepository.objects.acreate(project=project, remote_id=1, owner="app-spark", name=project.id)
    calls = []

    async def upload(self, tag=None):
        calls.append(tag)
        return SimpleNamespace(commit_sha=COMMIT)

    async def sign(package, *, expires_in):
        calls.append(expires_in)
        return "https://bkrepo.example.com/signed"

    monkeypatch.setattr("app_spark_api.publication.packaging.RepoPackager.aupload", upload)
    monkeypatch.setattr("app_spark_api.publication.packaging.agenerate_source_package_url", sign)

    source = await apackage_version(project, TAG)

    assert calls == [TAG, PACKAGE_URL_EXPIRES_IN]
    assert PACKAGE_URL_EXPIRES_IN <= 30 * 60
    # 版本号会出现在开发者中心的部署记录里：去掉 tag 里的斜杠，带上短 SHA。
    assert (source.version, source.package_url) == ("run-1-3f2a1bc", "https://bkrepo.example.com/signed")


async def test_a_missing_tag_is_explained(project, monkeypatch):
    await ProjectGitRepository.objects.acreate(project=project, remote_id=1, owner="app-spark", name=project.id)

    async def upload(self, tag=None):
        raise SourceRefNotFoundError(tag)

    monkeypatch.setattr("app_spark_api.publication.packaging.RepoPackager.aupload", upload)

    with pytest.raises(SourcePackagingError, match="找不到版本"):
        await apackage_version(project, TAG)
