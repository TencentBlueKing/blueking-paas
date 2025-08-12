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

from unittest import mock

import gitlab.exceptions
import pytest
from django_dynamic_fixture import G

from paasng.accessories.publish.market.models import ApplicationExtraInfo, Product, Tag
from paasng.bk_plugins.bk_plugins.models import BkPluginTag
from paasng.core.core.protections.exceptions import ConditionNotMatched
from paasng.infras.accounts.models import Oauth2TokenHolder, UserProfile
from paasng.infras.iam.helpers import add_role_members, remove_user_all_roles
from paasng.platform.applications.constants import ApplicationRole, AvailabilityLevel
from paasng.platform.engine.constants import DeployConditions
from paasng.platform.engine.workflow.protections import (
    ApplicationExtraInfoCondition,
    EnvProtectionCondition,
    ModuleEnvDeployInspector,
    PluginTagValidationCondition,
    ProductInfoCondition,
    RepoAccessCondition,
)
from paasng.platform.environments.constants import EnvRoleOperation
from paasng.platform.environments.models import EnvRoleProtection
from paasng.platform.sourcectl.models import GitProject
from paasng.platform.sourcectl.source_types import get_sourcectl_names

pytestmark = pytest.mark.django_db


@pytest.fixture()
def git_client(bk_module):
    """A fixture used to mock Git repo dependency"""
    with (
        mock.patch.object(bk_module, "get_source_obj"),
        mock.patch.object(GitProject, "parse_from_repo_url") as get_backends,
        mock.patch("paasng.platform.sourcectl.controllers.gitlab.GitLabApiClient") as client,
    ):
        get_backends.return_value = GitProject(name="baz", namespace="bar", type="dft_gitlab")
        yield client()


class TestProductInfoCondition:
    @pytest.mark.parametrize(
        ("env", "create_product", "ok"),
        [("prod", False, False), ("prod", True, True), ("stag", False, True), ("stag", True, True)],
    )
    def test_validate(self, bk_user, bk_module, env, create_product, ok):
        application = bk_module.application
        env = bk_module.get_envs(env)

        if create_product:
            G(Product, application=application)

        if ok:
            ProductInfoCondition(bk_user, env).validate()
        else:
            with pytest.raises(ConditionNotMatched) as exc_info:
                ProductInfoCondition(bk_user, env).validate()

            assert exc_info.value.action_name == DeployConditions.FILL_PRODUCT_INFO.value


class TestPluginTagCondition:
    @pytest.mark.parametrize(
        ("env", "create_tag", "ok"),
        [("prod", False, False), ("prod", True, True), ("stag", False, True), ("stag", True, True)],
    )
    def test_validate(self, bk_user, bk_plugin_app, env, create_tag, ok):
        bk_plugin_profile = bk_plugin_app.bk_plugin_profile

        if create_tag:
            tag_1 = G(BkPluginTag, code_name="sample-tag-code-1", name="sample-tag-1")
            bk_plugin_profile.tag = tag_1

        env = bk_plugin_app.get_default_module().envs.get(environment=env)
        if ok:
            PluginTagValidationCondition(bk_user, env).validate()
        else:
            with pytest.raises(ConditionNotMatched) as exc_info:
                PluginTagValidationCondition(bk_user, env).validate()

            assert exc_info.value.action_name == DeployConditions.FILL_PLUGIN_TAG_INFO.value


class TestEnvProtectionCondition:
    @pytest.mark.parametrize(
        ("user_role", "allowed_roles", "ok"),
        [
            (ApplicationRole.ADMINISTRATOR, [], True),
            (ApplicationRole.ADMINISTRATOR, [ApplicationRole.ADMINISTRATOR], True),
            (ApplicationRole.ADMINISTRATOR, [ApplicationRole.DEVELOPER], False),
            (ApplicationRole.DEVELOPER, [], True),
            (ApplicationRole.DEVELOPER, [ApplicationRole.ADMINISTRATOR], False),
            (ApplicationRole.DEVELOPER, [ApplicationRole.DEVELOPER], True),
            (ApplicationRole.DEVELOPER, [ApplicationRole.ADMINISTRATOR, ApplicationRole.DEVELOPER], True),
        ],
    )
    def test_validate(self, bk_user, bk_module, user_role, allowed_roles, ok):
        application = bk_module.application
        env = bk_module.get_envs("stag")

        remove_user_all_roles(application.code, bk_user.username)
        add_role_members(application.code, user_role, bk_user.username)

        for role in allowed_roles:
            EnvRoleProtection.objects.create(
                allowed_role=role.value, module_env=env, operation=EnvRoleOperation.DEPLOY.value
            )

        if ok:
            EnvProtectionCondition(bk_user, env).validate()
        else:
            with pytest.raises(ConditionNotMatched):
                EnvProtectionCondition(bk_user, env).validate()
            inspector = ModuleEnvDeployInspector(bk_user, env)
            inspector.conditions = [EnvProtectionCondition(bk_user, env)]
            assert [item.action_name for item in inspector.perform().failed_conditions] == [
                EnvProtectionCondition.action_name
            ]


class TestRepoAccessCondition:
    @pytest.mark.parametrize(
        ("source_type", "create_user_profile", "create_token_holder", "ok", "action_name"),
        [
            ("dft_gitlab", False, False, False, DeployConditions.NEED_TO_BIND_OAUTH_INFO),
            ("dft_gitlab", True, False, False, DeployConditions.NEED_TO_BIND_OAUTH_INFO),
            ("dft_gitlab", True, True, False, DeployConditions.DONT_HAVE_ENOUGH_PERMISSIONS),
            ("dft_gitlab", True, True, True, ...),
        ],
    )
    def test_validate(
        self, bk_user, bk_module, git_client, source_type, create_user_profile, create_token_holder, ok, action_name
    ):
        env = bk_module.get_envs("stag")
        bk_module.source_type = source_type
        bk_module.save()
        if create_user_profile:
            profile = G(UserProfile, user=bk_user)
            if create_token_holder:
                G(Oauth2TokenHolder, user=profile, provider=get_sourcectl_names().GitLab)

        if ok:
            assert RepoAccessCondition(bk_user, env).validate() is None
        else:

            def get_project_info(project):
                raise gitlab.exceptions.GitlabAuthenticationError

            git_client.get_project_info.side_effect = get_project_info
            with pytest.raises(ConditionNotMatched) as exc_info:
                RepoAccessCondition(bk_user, env).validate()

            assert exc_info.value.action_name == action_name.value
            inspector = ModuleEnvDeployInspector(bk_user, env)
            inspector.conditions = [RepoAccessCondition(bk_user, env)]
            assert [item.action_name for item in inspector.perform().failed_conditions] == [action_name.value]


class TestAppExtraInfoCondition:
    @pytest.mark.parametrize(
        ("create_extra_info", "set_availability_level", "set_tag", "ok"),
        [
            (False, False, False, False),
            (False, True, False, False),
            (True, False, True, True),
            (True, True, True, True),
        ],
    )
    def test_validate(self, bk_user, bk_module, create_extra_info, set_availability_level, set_tag, ok):
        application = bk_module.application
        env = bk_module.get_envs("stag")

        if create_extra_info:
            extra_info = G(ApplicationExtraInfo, application=application)
            if set_availability_level:
                extra_info.availability_level = AvailabilityLevel.STANDARD.value
                extra_info.save(update_fields=["availability_level"])
                extra_info.refresh_from_db()

            if set_tag:
                tag = G(Tag, name="sample-tag-1")
                extra_info.tag = tag
                extra_info.save(update_fields=["tag"])
                extra_info.refresh_from_db()

        if ok:
            ApplicationExtraInfoCondition(bk_user, env).validate()
        else:
            with pytest.raises(ConditionNotMatched) as exc_info:
                ApplicationExtraInfoCondition(bk_user, env).validate()

            assert exc_info.value.action_name == DeployConditions.FILL_EXTRA_INFO.value


class TestModuleEnvDeployInspector:
    @pytest.mark.parametrize(
        ("user_role", "allowed_roles", "create_token", "create_product", "set_extra_info", "expected"),
        [
            (
                ApplicationRole.DEVELOPER,
                [ApplicationRole.ADMINISTRATOR],
                False,
                False,
                False,
                [
                    DeployConditions.FILL_PRODUCT_INFO,
                    DeployConditions.CHECK_ENV_PROTECTION,
                    DeployConditions.NEED_TO_BIND_OAUTH_INFO,
                    DeployConditions.FILL_EXTRA_INFO,
                ],
            ),
            (
                ApplicationRole.OPERATOR,
                [ApplicationRole.ADMINISTRATOR],
                True,
                False,
                False,
                [
                    DeployConditions.FILL_PRODUCT_INFO,
                    DeployConditions.CHECK_ENV_PROTECTION,
                    DeployConditions.FILL_EXTRA_INFO,
                ],
            ),
            (
                ApplicationRole.ADMINISTRATOR,
                ...,
                True,
                False,
                False,
                [
                    DeployConditions.FILL_PRODUCT_INFO,
                    DeployConditions.FILL_EXTRA_INFO,
                ],
            ),
            (
                ...,
                ...,
                True,
                True,
                False,
                [
                    DeployConditions.FILL_EXTRA_INFO,
                ],
            ),
            (
                ...,
                ...,
                True,
                True,
                True,
                [],
            ),
        ],
    )
    def test(
        self,
        bk_user,
        bk_module,
        git_client,
        user_role,
        allowed_roles,
        create_token,
        create_product,
        set_extra_info,
        expected,
    ):
        application = bk_module.application
        env = bk_module.get_envs("prod")
        bk_module.source_type = get_sourcectl_names().GitLab
        bk_module.save()

        if user_role is not ...:
            remove_user_all_roles(application.code, bk_user.username)
            add_role_members(application.code, user_role, bk_user.username)

        if allowed_roles is not ...:
            for role in allowed_roles:
                EnvRoleProtection.objects.create(
                    allowed_role=role.value, module_env=env, operation=EnvRoleOperation.DEPLOY.value
                )

        if create_token:
            profile = G(UserProfile, user=bk_user)
            G(Oauth2TokenHolder, user=profile, provider=get_sourcectl_names().GitLab)

        if create_product:
            G(Product, application=application)

        if set_extra_info:
            tag = G(Tag, name="sample-tag-1")
            G(
                ApplicationExtraInfo,
                application=application,
                tag=tag,
                availability_level=AvailabilityLevel.STANDARD.value,
            )

        inspector = ModuleEnvDeployInspector(bk_user, env)
        assert [item.action_name for item in inspector.perform().failed_conditions] == [c.value for c in expected]
        assert inspector.all_matched is not len(expected)
