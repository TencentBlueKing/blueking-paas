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

"""Shortcuts shared by the API routes."""

from __future__ import annotations

import pytest
from django.http import Http404
from django.test import RequestFactory

from app_spark_api.core.projects.models import Project
from app_spark_api.core.shortcuts import aget_project_or_404
from app_spark_api.core.tenant.user import get_tenant
from tests.helpers import create_user

pytestmark = pytest.mark.django_db(transaction=True)


def make_request(user):
    request = RequestFactory().get("/")
    # `login_required` 通过后 django-ninja 把用户挂在这里，`authenticated_user` 从这里取。
    request.auth = user  # type: ignore[attr-defined]
    return request


async def test_aget_project_or_404_returns_a_project_the_caller_owns(bk_user):
    await Project.objects.acreate(
        id="spark-demo", name="Spark Demo", creator=bk_user, owner=bk_user, tenant_id=get_tenant(bk_user).id
    )

    project = await aget_project_or_404(make_request(bk_user), "spark-demo")

    assert project.pk == "spark-demo"


async def test_aget_project_or_404_hides_projects_the_caller_cannot_reach(bk_user):
    tenant_id = get_tenant(bk_user).id
    await Project.objects.acreate(
        id="other-owner", name="Theirs", creator=bk_user, owner=create_user().pk, tenant_id=tenant_id
    )
    await Project.objects.acreate(
        id="deleted-demo", name=None, creator=bk_user, owner=bk_user, tenant_id=tenant_id, is_deleted=True
    )

    for project_id in ("missing-demo", "other-owner", "deleted-demo"):
        with pytest.raises(Http404):
            await aget_project_or_404(make_request(bk_user), project_id)
