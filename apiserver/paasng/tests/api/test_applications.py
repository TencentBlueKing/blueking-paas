# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
import logging
from unittest import mock

import pytest
from django.conf import settings
from django.urls import reverse
from django_dynamic_fixture import G

from paas_wl.infras.cluster.constants import ClusterFeatureFlag
from paas_wl.infras.cluster.shim import RegionClusterService
from paasng.infras.accounts.constants import AccountFeatureFlag as AFF
from paasng.infras.accounts.models import AccountFeatureFlag, UserProfile
from paasng.misc.operations.constant import OperationType
from paasng.misc.operations.models import Operation
from paasng.platform.applications.constants import AppFeatureFlag, ApplicationRole, ApplicationType
from paasng.platform.applications.handlers import post_create_application, turn_on_bk_log_feature
from paasng.platform.applications.models import Application
from paasng.platform.bkapp_model.models import ModuleProcessSpec
from paasng.platform.declarative.handlers import get_desc_handler
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.models import BuildConfig
from paasng.platform.modules.models.module import Module
from paasng.platform.sourcectl.connector import IntegratedSvnAppRepoConnector, SourceSyncResult
from paasng.utils.basic import get_username_by_bkpaas_user_id
from paasng.utils.error_codes import error_codes
from tests.conftest import CLUSTER_NAME_FOR_TESTING
from tests.utils.auth import create_user
from tests.utils.helpers import configure_regions, generate_random_string

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


logger = logging.getLogger(__name__)


@pytest.fixture()
def another_user(request):
    """Generate a random user"""
    user = create_user()
    return user


@pytest.fixture(autouse=True)
def _turn_on_bk_log_feature():
    post_create_application.connect(turn_on_bk_log_feature)
    yield
    post_create_application.disconnect(turn_on_bk_log_feature)


class TestMembershipViewset:
    def test_list_succeed(self, api_client, bk_app):
        url = reverse("api.applications.members", kwargs=dict(code=bk_app.code))
        response = api_client.get(url)
        assert len(response.data["results"]) == 1

    @pytest.mark.parametrize(
        ("role", "status", "ok"),
        [
            (..., 403, False),
            (ApplicationRole.ADMINISTRATOR, 200, True),
            (ApplicationRole.DEVELOPER, 200, True),
            (ApplicationRole.OPERATOR, 200, True),
        ],
    )
    def test_list_with_another_user(self, api_client, bk_app, bk_user, another_user, role, status, ok):
        url = reverse("api.applications.members", kwargs=dict(code=bk_app.code))
        if role is not ...:
            from paasng.infras.iam.helpers import add_role_members

            add_role_members(bk_app.code, role, get_username_by_bkpaas_user_id(another_user.pk))

        api_client.force_authenticate(user=another_user)
        response = api_client.get(url)
        assert response.status_code == status
        if ok:
            assert len(response.data["results"]) == 2
            test = {
                m["user"]["username"]: dict(code=bk_app.code, role=m["roles"][0]["id"])
                for m in response.data["results"]
            }
            assert test[another_user.username]["code"] == bk_app.code
            assert test[another_user.username]["role"] == role.value

    @pytest.mark.parametrize(
        ("role", "request_user_idx", "to_create_user_idx", "status"),
        [
            # success case
            (ApplicationRole.ADMINISTRATOR, 0, 1, 201),
            (ApplicationRole.DEVELOPER, 0, 1, 201),
            # invalid args
            (None, 0, 0, 400),
            (None, 0, 1, 400),
            # forbidden
            (ApplicationRole.ADMINISTRATOR, 1, 0, 403),
            (ApplicationRole.DEVELOPER, 1, 1, 403),
        ],
    )
    def test_create(
        self, api_client, bk_app, bk_user, another_user, role, request_user_idx, to_create_user_idx, status
    ):
        user_choices = [bk_user, another_user]
        cur_user = user_choices[request_user_idx]
        new_user = user_choices[to_create_user_idx]

        url = reverse("api.applications.members", kwargs=dict(code=bk_app.code))
        role_value = role.value if isinstance(role, ApplicationRole) else "invalid_role"
        data = [{"user": {"username": new_user.username, "id": new_user.pk}, "roles": [{"id": role_value}]}]

        api_client.force_authenticate(cur_user)
        response = api_client.post(url, data=data)
        assert response.status_code == status

    @pytest.mark.parametrize(
        ("another_user_role", "request_user_idx", "be_deleted_idx", "status"),
        [
            (ApplicationRole.ADMINISTRATOR, 0, 0, 204),
            (ApplicationRole.DEVELOPER, 0, 0, 400),
            (ApplicationRole.ADMINISTRATOR, 0, 1, 204),
            (ApplicationRole.DEVELOPER, 0, 1, 204),
            (ApplicationRole.ADMINISTRATOR, 1, 0, 204),
            (ApplicationRole.DEVELOPER, 1, 0, 403),
            (ApplicationRole.ADMINISTRATOR, 1, 1, 204),
            (ApplicationRole.DEVELOPER, 1, 1, 403),
        ],
    )
    def test_delete(
        self, api_client, bk_app, bk_user, another_user, another_user_role, request_user_idx, be_deleted_idx, status
    ):
        from paasng.infras.iam.helpers import add_role_members, fetch_application_members

        add_role_members(bk_app.code, another_user_role, get_username_by_bkpaas_user_id(another_user.pk))
        user_choices = [bk_user, another_user, create_user("dummy")]
        cur_user = user_choices[request_user_idx]
        user_to_delete = user_choices[be_deleted_idx]

        url = reverse("api.applications.members.detail", kwargs=dict(code=bk_app.code, user_id=user_to_delete.pk))

        api_client.force_authenticate(cur_user)
        response = api_client.delete(url)
        assert response.status_code == status

        if status == 204:
            assert len(fetch_application_members(bk_app.code)) == 1
        else:
            assert len(fetch_application_members(bk_app.code)) == 2

    @pytest.mark.parametrize(
        ("another_user_role", "request_user_idx", "status", "code"),
        [
            # 创建者也可以离开应用
            (ApplicationRole.ADMINISTRATOR, 0, 204, ...),
            (ApplicationRole.ADMINISTRATOR, 1, 204, ...),
            (ApplicationRole.DEVELOPER, 1, 204, ...),
            (ApplicationRole.ADMINISTRATOR, 2, 403, "ERROR"),
        ],
    )
    def test_level(self, api_client, bk_app, bk_user, another_user, another_user_role, request_user_idx, status, code):
        from paasng.infras.iam.helpers import add_role_members, fetch_application_members

        add_role_members(bk_app.code, another_user_role, get_username_by_bkpaas_user_id(another_user.pk))
        user_choices = [bk_user, another_user, create_user("dummy")]
        cur_user = user_choices[request_user_idx]

        url = reverse("api.applications.members.leave", kwargs=dict(code=bk_app.code))
        api_client.force_authenticate(cur_user)
        response = api_client.post(url)
        assert response.status_code == status

        user_count = 1 if status == 204 else 2
        assert len(fetch_application_members(bk_app.code)) == user_count

        if code is not ...:
            assert response.json()["code"] == code

    def test_level_last_admin(self, api_client, bk_app, bk_user, another_user):
        from paasng.infras.iam.helpers import add_role_members, fetch_application_members, remove_user_all_roles

        add_role_members(bk_app.code, ApplicationRole.ADMINISTRATOR, get_username_by_bkpaas_user_id(another_user.pk))
        remove_user_all_roles(bk_app.code, get_username_by_bkpaas_user_id(bk_user.pk))
        add_role_members(bk_app.code, ApplicationRole.DEVELOPER, get_username_by_bkpaas_user_id(bk_user.pk))
        cur_user = another_user

        url = reverse("api.applications.members.leave", kwargs=dict(code=bk_app.code))
        api_client.force_authenticate(cur_user)
        response = api_client.post(url)
        assert response.status_code == 400
        assert len(fetch_application_members(bk_app.code)) == 2
        assert response.json()["code"] == "MEMBERSHIP_DELETE_FAILED"


class TestApplicationCreateWithEngine:
    """Test application creation APIs with engine enabled"""

    @pytest.mark.usefixtures("_init_tmpls")
    @pytest.mark.parametrize(
        ("type", "desired_type", "creation_succeeded"),
        [
            ("default", "default", True),
            ("cloud_native", "cloud_native", True),
            ("engineless_app", "engineless_app", False),
        ],
    )
    def test_create_different_types(
        self,
        type,
        desired_type,
        creation_succeeded,
        api_client,
        mock_wl_services_in_creation,
        mock_initialize_vcs_with_template,
        settings,
    ):
        # Turn on "allow_creation" in bk_plugin configs
        settings.BK_PLUGIN_CONFIG = {"allow_creation": True}
        with mock.patch.object(IntegratedSvnAppRepoConnector, "sync_templated_sources") as mocked_sync:
            # Mock return value of syncing template
            mocked_sync.return_value = SourceSyncResult(dest_type="mock")

            random_suffix = generate_random_string(length=6)
            response = api_client.post(
                "/api/bkapps/applications/v2/",
                data={
                    "region": settings.DEFAULT_REGION_NAME,
                    "type": type,
                    "code": f"uta-{random_suffix}",
                    "name": f"uta-{random_suffix}",
                    "engine_params": {
                        "source_origin": SourceOrigin.AUTHORIZED_VCS.value,
                        "source_control_type": "dft_bk_svn",
                        "source_init_template": settings.DUMMY_TEMPLATE_NAME,
                    },
                },
            )
            if creation_succeeded:
                assert response.status_code == 201
                assert response.json()["application"]["type"] == desired_type
            else:
                assert response.status_code == 400
                assert response.json()["detail"] == '已开启引擎，类型不能为 "engineless_app"'

    @pytest.mark.usefixtures("_init_tmpls")
    @pytest.mark.parametrize(
        ("source_origin", "source_repo_url", "source_control_type", "with_feature_flag", "is_success"),
        [
            (
                SourceOrigin.BK_LESS_CODE,
                "http://dummy.git",
                "",
                True,
                True,
            ),
            (
                SourceOrigin.BK_LESS_CODE,
                "http://dummy.git",
                "",
                False,
                False,
            ),
            (SourceOrigin.IMAGE_REGISTRY, "127.0.0.1:5000/library/python", "dft_docker", True, True),
            (SourceOrigin.IMAGE_REGISTRY, "127.0.0.1:5000/library/python", "dft_docker", False, True),
        ],
    )
    def test_create_nondefault_origin(
        self,
        api_client,
        bk_user,
        mock_wl_services_in_creation,
        source_origin,
        source_repo_url,
        source_control_type,
        with_feature_flag,
        is_success,
    ):
        # Set user feature flag
        AccountFeatureFlag.objects.set_feature(bk_user, AFF.ALLOW_CHOOSE_SOURCE_ORIGIN, with_feature_flag)

        random_suffix = generate_random_string(length=6)
        response = api_client.post(
            "/api/bkapps/applications/v2/",
            data={
                "region": settings.DEFAULT_REGION_NAME,
                "code": f"uta-{random_suffix}",
                "name": f"uta-{random_suffix}",
                "engine_params": {
                    "source_origin": source_origin,
                    "source_repo_url": source_repo_url,
                    "source_init_template": settings.DUMMY_TEMPLATE_NAME,
                    "source_control_type": source_control_type,
                },
            },
        )
        desired_status_code = 201 if is_success else 400
        assert response.status_code == desired_status_code


class TestApplicationCreateWithoutEngine:
    """Test application creation APIs with engine disabled"""

    @pytest.mark.parametrize("url", ["/api/bkapps/applications/v2/", "/api/bkapps/third-party/"])
    def test_create_non_engine(self, api_client, url):
        random_suffix = generate_random_string(length=6)
        response = api_client.post(
            url,
            data={
                "region": settings.DEFAULT_REGION_NAME,
                "code": f"uta-{random_suffix}",
                "name": f"uta-{random_suffix}",
                "engine_enabled": False,
                "market_params": {},
            },
        )
        assert response.status_code == 201
        assert response.json()["application"]["type"] == "engineless_app"

    @pytest.mark.parametrize("url", ["/api/bkapps/applications/v2/", "/api/bkapps/third-party/"])
    @pytest.mark.parametrize(
        ("profile_regions", "region", "creation_success"),
        [
            (["r1"], "r1", True),
            (["r1", "r2"], "r1", True),
            (["r1"], "r2", False),
        ],
    )
    def test_region_permission_control(self, bk_user, api_client, url, profile_regions, region, creation_success):
        """When user has or doesn't have permission, test application creation."""
        with configure_regions(["r1", "r2"]):
            user_profile = UserProfile.objects.get_profile(bk_user)
            user_profile.enable_regions = ";".join(profile_regions)
            user_profile.save()

            random_suffix = generate_random_string(length=6)
            response = api_client.post(
                url,
                data={
                    "region": region,
                    "code": f"uta-{random_suffix}",
                    "name": f"uta-{random_suffix}",
                    "engine_enabled": False,
                    "market_params": {},
                },
            )
            desired_status_code = 201 if creation_success else 403
            assert response.status_code == desired_status_code


class TestApplicationUpdate:
    """Test update application API"""

    @pytest.mark.usefixtures("_register_app_core_data")
    def test_normal(self, api_client, bk_app_full, bk_user, random_name):
        response = api_client.put(
            "/api/bkapps/applications/{}/".format(bk_app_full.code),
            data={"name": random_name},
        )
        assert response.status_code == 200
        assert Application.objects.get(pk=bk_app_full.pk).name == random_name

    def test_duplicated(self, api_client, bk_app, bk_user, random_name):
        G(Application, name=random_name)
        response = api_client.put(
            "/api/bkapps/applications/{}/".format(bk_app.code),
            data={"name": random_name},
        )
        assert response.status_code == 400
        assert response.json()["code"] == "VALIDATION_ERROR"
        assert f"应用名称 为 {random_name} 的应用已存在" in response.json()["detail"]

    def test_desc_app(self, api_client, bk_user, random_name, mock_wl_services_in_creation):
        get_desc_handler(
            dict(
                spec_version=2,
                app={"bk_app_code": random_name, "bk_app_name": random_name},
                modules={random_name: {"is_default": True, "language": "python"}},
            )
        ).handle_app(bk_user)
        app = Application.objects.get(code=random_name)
        response = api_client.put(
            "/api/bkapps/applications/{}/".format(app.code),
            data={"name": random_name},
        )
        assert response.status_code == 400
        assert response.json()["code"] == "APP_RES_PROTECTED"


class TestApplicationDeletion:
    """Test delete application API"""

    @pytest.mark.usefixtures("_with_empty_live_addrs")
    def test_normal(
        self,
        api_client,
        bk_app,
        bk_user,
        mock_wl_services_in_creation,
    ):
        assert not Operation.objects.filter(application=bk_app, type=OperationType.DELETE_APPLICATION.value).exists()
        with mock.patch("paasng.platform.modules.manager.delete_module_related_res"):
            response = api_client.delete("/api/bkapps/applications/{}/".format(bk_app.code))
        assert response.status_code == 204
        assert Operation.objects.filter(application=bk_app, type=OperationType.DELETE_APPLICATION.value).exists()

    @pytest.mark.usefixtures("_with_empty_live_addrs")
    def test_rollback(
        self,
        api_client,
        bk_app,
        bk_user,
        mock_wl_services_in_creation,
    ):
        assert not Operation.objects.filter(application=bk_app, type=OperationType.DELETE_APPLICATION.value).exists()
        with mock.patch(
            "paasng.platform.applications.views.ApplicationViewSet._delete_all_module",
            side_effect=error_codes.CANNOT_DELETE_APP,
        ):
            response = api_client.delete("/api/bkapps/applications/{}/".format(bk_app.code))
        assert response.status_code == 400
        assert Operation.objects.filter(application=bk_app, type=OperationType.DELETE_APPLICATION.value).exists()


class TestCreateBkPlugin:
    """Test 'bk_plugin' type application's creation"""

    @pytest.mark.usefixtures("_init_tmpls")
    def test_normal(self, api_client, mock_wl_services_in_creation, settings):
        settings.BK_PLUGIN_CONFIG = {"allow_creation": True}
        response = self._send_creation_request(api_client)

        assert response.status_code == 201, f'error: {response.json()["detail"]}'
        assert response.json()["application"]["is_plugin_app"] is True
        # TODO: Update tests when bk_plugin supports multiple languages
        assert response.json()["application"]["language"] == "Python"
        assert response.json()["application"]["modules"][0]["repo"] is not None

    def test_forbidden_via_config(self, api_client, settings):
        settings.BK_PLUGIN_CONFIG = {"allow_creation": False}
        response = self._send_creation_request(api_client)

        assert response.status_code == 400, "the creation of bk_plugin must fail"

    def _send_creation_request(self, api_client):
        random_suffix = generate_random_string(length=6)
        return api_client.post(
            "/api/bkapps/applications/v2/",
            data={
                "region": settings.DEFAULT_REGION_NAME,
                "type": ApplicationType.CLOUD_NATIVE,
                "is_plugin_app": True,
                "code": f"uta-{random_suffix}",
                "name": f"uta-{random_suffix}",
                "engine_params": {
                    "source_origin": SourceOrigin.AUTHORIZED_VCS.value,
                    "source_control_type": "dft_gitlab",
                    "source_repo_url": "http://example.com/default/git.git",
                },
            },
        )


class TestCreateCloudNativeApp:
    """Test 'cloud_native' type application's creation"""

    @pytest.fixture(autouse=True)
    def _setup(self, mock_wl_services_in_creation, mock_initialize_vcs_with_template, _init_tmpls, bk_user, settings):
        settings.CLOUD_NATIVE_APP_DEFAULT_CLUSTER = CLUSTER_NAME_FOR_TESTING
        AccountFeatureFlag.objects.set_feature(bk_user, AFF.ALLOW_CREATE_CLOUD_NATIVE_APP, True)

    def test_create_with_image(self, api_client):
        """托管方式：仅镜像"""
        random_suffix = generate_random_string(length=6)
        image_credential_name = generate_random_string(length=6)
        image_repository = "strm/helloworld-http"
        response = api_client.post(
            "/api/bkapps/cloud-native/",
            data={
                "region": settings.DEFAULT_REGION_NAME,
                "code": f"uta-{random_suffix}",
                "name": f"uta-{random_suffix}",
                "bkapp_spec": {
                    "build_config": {
                        "build_method": "custom_image",
                        "image_repository": image_repository,
                        "image_credential": {"name": image_credential_name, "password": "123456", "username": "test"},
                    },
                    "processes": [
                        {
                            "name": "web",
                            "command": ["bash", "/app/start_web.sh"],
                            "env_overlay": {
                                "stag": {"environment_name": "stag", "target_replicas": 1, "plan_name": "2C1G"},
                                "prod": {"environment_name": "prod", "target_replicas": 2, "plan_name": "2C1G"},
                            },
                        }
                    ],
                },
                "source_config": {
                    "source_origin": SourceOrigin.CNATIVE_IMAGE,
                    "source_repo_url": image_repository,
                },
            },
        )
        assert response.status_code == 201, f'error: {response.json()["detail"]}'
        app_data = response.json()["application"]
        assert app_data["type"] == "cloud_native"
        assert app_data["modules"][0]["web_config"]["build_method"] == "custom_image"
        assert app_data["modules"][0]["web_config"]["artifact_type"] == "none"

        module = Module.objects.get(id=app_data["modules"][0]["id"])
        cfg = BuildConfig.objects.get_or_create_by_module(module)
        assert cfg.image_repository == image_repository
        assert cfg.image_credential_name == image_credential_name

        process_spec = ModuleProcessSpec.objects.get(module=module, name="web")
        assert process_spec.image is None
        assert process_spec.command == ["bash", "/app/start_web.sh"]
        assert process_spec.get_target_replicas("stag") == 1
        assert process_spec.get_target_replicas("prod") == 2

    @pytest.mark.usefixtures("_init_tmpls")
    @mock.patch("paasng.platform.modules.helpers.ModuleRuntimeBinder")
    @mock.patch("paasng.platform.engine.configurations.building.ModuleRuntimeManager")
    def test_create_with_buildpack(self, mocked_binder, mocked_manager, api_client):
        """托管方式：源码 & 镜像（使用 buildpack 进行构建）"""
        mocked_binder().bind_bp_stack.return_value = None
        mocked_manager().get_slug_builder.return_value = mock.MagicMock(is_cnb_runtime=True, environments={})

        random_suffix = generate_random_string(length=6)
        response = api_client.post(
            "/api/bkapps/cloud-native/",
            data={
                "region": settings.DEFAULT_REGION_NAME,
                "code": f"uta-{random_suffix}",
                "name": f"uta-{random_suffix}",
                "bkapp_spec": {"build_config": {"build_method": "buildpack"}},
                "source_config": {
                    "source_init_template": settings.DUMMY_TEMPLATE_NAME,
                    "source_origin": SourceOrigin.AUTHORIZED_VCS,
                    "source_repo_url": "https://github.com/octocat/helloWorld.git",
                    "source_repo_auth_info": {},
                },
            },
        )
        assert response.status_code == 201, f'error: {response.json()["detail"]}'
        app_data = response.json()["application"]
        assert app_data["type"] == "cloud_native"
        assert app_data["modules"][0]["web_config"]["build_method"] == "buildpack"
        assert app_data["modules"][0]["web_config"]["artifact_type"] == "image"

    @pytest.mark.usefixtures("_init_tmpls")
    def test_create_with_dockerfile(self, api_client):
        """托管方式：源码 & 镜像（使用 dockerfile 进行构建）"""
        random_suffix = generate_random_string(length=6)
        response = api_client.post(
            "/api/bkapps/cloud-native/",
            data={
                "region": settings.DEFAULT_REGION_NAME,
                "code": f"uta-{random_suffix}",
                "name": f"uta-{random_suffix}",
                "bkapp_spec": {"build_config": {"build_method": "dockerfile", "dockerfile_path": "Dockerfile"}},
                "source_config": {
                    "source_init_template": "docker",
                    "source_origin": SourceOrigin.AUTHORIZED_VCS,
                    "source_repo_url": "https://github.com/octocat/helloWorld.git",
                    "source_repo_auth_info": {},
                },
            },
        )
        assert response.status_code == 201, f'error: {response.json()["detail"]}'
        app_data = response.json()["application"]
        assert app_data["type"] == "cloud_native"
        assert app_data["modules"][0]["web_config"]["build_method"] == "dockerfile"
        assert app_data["modules"][0]["web_config"]["artifact_type"] == "image"

    @pytest.mark.usefixtures("_init_tmpls")
    def test_create_with_bk_log_feature(self, api_client, settings):
        """测试创建应用时开启日志平台功能特性"""
        cluster = RegionClusterService(settings.DEFAULT_REGION_NAME).get_default_cluster()
        cluster.feature_flags[ClusterFeatureFlag.ENABLE_BK_LOG_COLLECTOR] = True
        cluster.save()

        random_suffix = generate_random_string(length=6)
        response = api_client.post(
            "/api/bkapps/cloud-native/",
            data={
                "region": settings.DEFAULT_REGION_NAME,
                "code": f"uta-{random_suffix}",
                "name": f"uta-{random_suffix}",
                "bkapp_spec": {"build_config": {"build_method": "dockerfile", "dockerfile_path": "Dockerfile"}},
                "source_config": {
                    "source_init_template": "docker",
                    "source_origin": SourceOrigin.AUTHORIZED_VCS,
                    "source_repo_url": "https://github.com/octocat/helloWorld.git",
                    "source_repo_auth_info": {},
                },
            },
        )
        assert response.status_code == 201, f'error: {response.json()["detail"]}'
        application = Application.objects.get(code=f"uta-{random_suffix}")
        assert application.feature_flag.has_feature(AppFeatureFlag.ENABLE_BK_LOG_COLLECTOR)
