# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
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

import pytest
from django_dynamic_fixture import G

from paasng.infras.accounts.models import Scope
from paasng.platform.sourcectl.exceptions import PackageAlreadyExists
from paasng.platform.sourcectl.models import GitProject, GitRepository, SourcePackage, SPStat, SPStoragePolicy

pytestmark = [pytest.mark.django_db]


def git_project_maker(url, sourcectl_type="dummy"):
    return GitProject.parse_from_path_with_namespace(url, sourcectl_type=sourcectl_type)


@pytest.mark.parametrize(
    ("repo_url", "expected"),
    [
        ("https://foo.com/bar/baz/qux", "bar/baz/qux"),
        ("https://foo.com/bar/baz/qux.git", "bar/baz/qux"),
    ],
)
def test_git_alias_name(repo_url, expected):
    assert G(GitRepository, repo_url=repo_url).get_repo_fullname() == expected


class TestGitProjectWithScope:
    @pytest.fixture()
    def projects(self):
        return [
            git_project_maker("http://fake-gitlab/namespace/project.git"),
            git_project_maker("http://fake-gitlab/v3-test-group/project.git"),
            git_project_maker("http://fake-gitlab/admin_yu/Sky-net.git"),
            git_project_maker("http://fake-gitlab/admin/Sky-net.git"),
            git_project_maker("http://fake-gitlab/admin_yu/Sky_net.git"),
        ]

    def test_has_permission_for_user(self, projects):
        scope = Scope.parse_from_str("user:user")
        for project in projects:
            assert scope.cover_project(project), "user:user必须都有权限"

    def test_has_permission_for_group(self, projects):
        scope = Scope.parse_from_str("group:v3-test-group")
        for project in projects:
            has_permission = scope.cover_project(project)
            if project.namespace == "v3-test-group":
                assert has_permission, "namespace == v3-test-group 必须有权限"
            else:
                assert not has_permission, "namespace != v3-test-group 必须没权限"

    def test_has_permission_for_project(self, projects):
        scope = Scope.parse_from_str("project:admin_yu/Sky-net")
        for project in projects:
            has_permission = scope.cover_project(project)
            if project.namespace == "admin_yu" and project.name == "Sky-net":
                assert has_permission, "namespace == admin_yu and name == Sky-net 必须有权限"
            else:
                assert not has_permission, "namespace != admin_yu or name != Sky-net  必须没权限"


@pytest.mark.parametrize(
    "policy",
    [
        SPStoragePolicy(
            engine="foo",
            path="bar",
            url="scheme://bucket/bar",
            stat=SPStat(name="name", version="v1", size=1, meta_info={}, sha256_signature="signature"),
        ),
    ],
)
@pytest.mark.django_db()
def test_store_package(bk_module, bk_user, policy):
    package = SourcePackage.objects.store(bk_module, policy, operator=bk_user)
    assert package.module == bk_module

    assert package.version == policy.stat.version
    assert package.sha256_signature == policy.stat.sha256_signature
    assert package.package_size == policy.stat.size
    assert package.meta_info == policy.stat.meta_info

    assert package.storage_engine == policy.engine
    assert package.storage_path == policy.path

    assert package.owner == bk_user.pk


@pytest.mark.parametrize(
    ("policy", "raised"),
    [
        (
            SPStoragePolicy(
                engine="foo",
                path="bar",
                url="scheme://bucket/bar",
                stat=SPStat(name="name", version="v1", size=1, meta_info={}, sha256_signature="signature"),
            ),
            True,
        ),
        (
            SPStoragePolicy(
                engine="foo",
                path="bar",
                url="scheme://bucket/bar",
                stat=SPStat(name="name", version="v1", size=1, meta_info={}, sha256_signature="signature"),
                allow_overwrite=True,
            ),
            False,
        ),
    ],
)
@pytest.mark.django_db()
def test_overwrite_package(bk_user, bk_module, policy, raised):
    SourcePackage.objects.store(bk_module, policy, operator=bk_user)
    if raised:
        with pytest.raises(PackageAlreadyExists):
            SourcePackage.objects.store(bk_module, policy, operator=bk_user)
    else:
        SourcePackage.objects.store(bk_module, policy, operator=bk_user)
