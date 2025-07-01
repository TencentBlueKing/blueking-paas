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
from moby_distribution.registry.exceptions import AuthFailed, PermissionDeny

from paas_wl.workloads.images.models import AppUserCredential
from paasng.accessories.publish.market.models import ApplicationExtraInfo, Product, Tag
from paasng.bk_plugins.bk_plugins.models import BkPluginTag
from paasng.core.core.protections.exceptions import ConditionNotMatched
from paasng.infras.accounts.models import Oauth2TokenHolder, UserProfile
from paasng.infras.iam.helpers import add_role_members, remove_user_all_roles
from paasng.platform.applications.constants import ApplicationRole, ApplicationType, AvailabilityLevel
from paasng.platform.engine.constants import DeployConditions, RuntimeType
from paasng.platform.engine.workflow.protections import (
    ApplicationExtraInfoCondition,
    EnvProtectionCondition,
    ImageRepositoryCondition,
    ModuleEnvDeployInspector,
    PluginTagValidationCondition,
    ProductInfoCondition,
    RepoAccessCondition,
)
from paasng.platform.environments.constants import EnvRoleOperation
from paasng.platform.environments.models import EnvRoleProtection
from paasng.platform.modules.models import BuildConfig
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


@pytest.mark.django_db(databases=["default", "workloads"])
class TestImageRepositoryCondition:
    @pytest.mark.parametrize(
        (
            "app_type",
            "runtime_type",
            "set_image_repo",
            "repo_access_result",
            "set_credential",
            "credential_valid",
            "expected_result",
        ),
        [
            # 自定义镜像类型且是云原生应用 - 直接通过
            (ApplicationType.CLOUD_NATIVE, RuntimeType.CUSTOM_IMAGE, False, None, False, None, True),
            # 未配置镜像仓库 - 失败
            (ApplicationType.DEFAULT, RuntimeType.CUSTOM_IMAGE, False, None, False, None, False),
            # 公共镜像仓库访问成功 - 通过
            (ApplicationType.DEFAULT, RuntimeType.CUSTOM_IMAGE, True, "public_success", False, None, True),
            # 需要权限但私有凭证访问成功 - 通过
            (ApplicationType.DEFAULT, RuntimeType.CUSTOM_IMAGE, True, "private_success", True, True, True),
            # 镜像仓库地址无效 - 失败
            (ApplicationType.DEFAULT, RuntimeType.CUSTOM_IMAGE, True, "invalid_repo", False, None, False),
            # 凭证不存在 - 失败
            (ApplicationType.DEFAULT, RuntimeType.CUSTOM_IMAGE, True, "private_required", False, None, False),
            # 凭证验证失败 - 失败
            (ApplicationType.DEFAULT, RuntimeType.CUSTOM_IMAGE, True, "private_required", True, False, False),
        ],
    )
    def test_validate(
        self,
        bk_user,
        bk_module,
        mocker,
        app_type,
        runtime_type,
        set_image_repo,
        repo_access_result,
        set_credential,
        credential_valid,
        expected_result,
    ):
        # 设置应用类型和运行时类型
        build_config = self._setup_module_and_build_config(bk_module, app_type, runtime_type, mocker)
        if set_image_repo:
            build_config.image_repository = "registry.example.com/test/image:latest"

            # 设置凭证名称
            if set_credential:
                credential_name = "test-credential"
                build_config.image_credential_name = credential_name

                # 创建凭证信息
                if credential_valid:
                    G(
                        AppUserCredential,
                        application_id=bk_module.application_id,
                        name=credential_name,
                        username="test_user",
                        password="test_pass",
                    )

            build_config.save()

        # 模拟 DockerRegistryController 行为
        self._setup_docker_registry_mock(mocker, repo_access_result, credential_valid)

        # 执行验证
        env = bk_module.get_envs().first()
        condition = ImageRepositoryCondition(bk_user, env)

        if expected_result:
            assert condition.validate() is None
        else:
            with pytest.raises(ConditionNotMatched) as exc_info:
                condition.validate()

            # 根据不同情况确定正确的 action_name
            if not set_image_repo or repo_access_result == "invalid_repo":
                expected_action = DeployConditions.CHECK_IMAGE_REPOSITORY.value
            else:
                expected_action = DeployConditions.CHECK_IMAGE_CREDENTIAL.value

            assert exc_info.value.action_name == expected_action

    def _setup_module_and_build_config(self, bk_module, app_type, runtime_type, mocker):
        """设置应用类型和模块运行时类型"""
        bk_module.application.type = app_type
        bk_module.application.save()

        module_specs_mock = mocker.patch("paasng.platform.modules.specs.ModuleSpecs")
        module_specs_mock.return_value.runtime_type = runtime_type

        build_config = BuildConfig.objects.get_or_create_by_module(module=bk_module)

        build_config.build_method = runtime_type
        build_config.save()

        return build_config

    def _setup_docker_registry_mock(self, mocker, repo_access_result, credential_valid):
        """设置 DockerRegistryController 的模拟行为"""
        mock = mocker.patch("paasng.platform.engine.workflow.protections.DockerRegistryController")
        registry_instance = mock.return_value

        if repo_access_result == "public_success":
            registry_instance.list_alternative_versions.return_value = ["v1.0", "v2.0"]
        elif repo_access_result == "invalid_repo":
            registry_instance.list_alternative_versions.side_effect = Exception("invalid repository")
        elif repo_access_result == "private_required":
            # 私有镜像
            def create_side_effect(credential_valid):
                call_count = 0

                def side_effect(*args, **kwargs):
                    nonlocal call_count
                    call_count += 1

                    if call_count == 1:
                        raise PermissionDeny("permission denied")
                    elif credential_valid:
                        return ["v1.0", "v2.0"]
                    else:
                        raise AuthFailed("auth failed")

                return side_effect

            registry_instance.list_alternative_versions.side_effect = create_side_effect(credential_valid)

        return registry_instance


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
                [DeployConditions.FILL_EXTRA_INFO],
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
