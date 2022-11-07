# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import logging
from unittest import mock

import pytest
from django.conf import settings
from django.urls import reverse
from django_dynamic_fixture import G

from paasng.accounts.constants import AccountFeatureFlag as AFF
from paasng.accounts.models import AccountFeatureFlag, UserProfile
from paasng.dev_resources.sourcectl.connector import IntegratedSvnAppRepoConnector, SourceSyncResult
from paasng.extensions.declarative.handlers import get_desc_handler
from paasng.platform.applications.constants import ApplicationRole
from paasng.platform.applications.models import Application, ApplicationMembership
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.operations.constant import OperationType
from paasng.platform.operations.models import Operation
from paasng.utils.error_codes import error_codes
from tests.utils.auth import create_user
from tests.utils.helpers import configure_regions, generate_random_string

pytestmark = pytest.mark.django_db


logger = logging.getLogger(__name__)


@pytest.fixture
def another_user(request):
    """Generate a random user"""
    user = create_user()
    return user


@pytest.fixture(autouse=True, scope="session")
def mock_sync_developers_to_sentry():
    with mock.patch("paasng.platform.applications.views.sync_developers_to_sentry"):
        yield


class TestMembershipViewset:
    def test_list_succeed(self, api_client, bk_app):
        url = reverse("api.applications.members", kwargs=dict(code=bk_app.code))
        response = api_client.get(url)
        assert len(response.data['results']) == 1

    @pytest.mark.parametrize(
        "role, status, ok",
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
            G(
                ApplicationMembership,
                application=bk_app,
                user=another_user.pk,
                role=role.value,
                region=settings.DEFAULT_REGION_NAME,
            )

        api_client.force_authenticate(user=another_user)
        response = api_client.get(url)
        assert response.status_code == status
        if ok:
            assert len(response.data['results']) == 2
            membership = response.data['results'][0]
            test = {
                m['user']["username"]: dict(code=membership["application"]["code"], role=m["role"]["id"])
                for m in response.data["results"]
            }
            assert test[another_user.username]["code"] == bk_app.code
            assert test[another_user.username]["role"] == role.value

    @pytest.mark.parametrize(
        "role, request_user_idx, to_create_user_idx, status",
        [
            # duplicated case
            (ApplicationRole.ADMINISTRATOR, 0, 0, 400),
            (ApplicationRole.DEVELOPER, 0, 0, 400),
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
        role_value = role.value if isinstance(role, ApplicationRole) else 'invalid_role'
        data = [dict(user=dict(username=new_user.username, id=new_user.pk), role=dict(id=role_value))]

        api_client.force_authenticate(cur_user)
        response = api_client.post(url, data=data)
        assert response.status_code == status

    @pytest.mark.parametrize(
        "another_user_role, request_user_idx, be_deleted_idx, status",
        [
            (ApplicationRole.ADMINISTRATOR, 0, 0, 204),
            (ApplicationRole.DEVELOPER, 0, 0, 400),
            (ApplicationRole.ADMINISTRATOR, 0, 1, 204),
            (ApplicationRole.DEVELOPER, 0, 1, 204),
            (ApplicationRole.ADMINISTRATOR, 1, 0, 204),
            (ApplicationRole.DEVELOPER, 1, 0, 403),
            (ApplicationRole.ADMINISTRATOR, 1, 1, 204),
            (ApplicationRole.DEVELOPER, 1, 1, 403),
            # user not found in memberships
            (ApplicationRole.ADMINISTRATOR, 0, 2, 404),
            (ApplicationRole.ADMINISTRATOR, 1, 2, 404),
        ],
    )
    def test_delete(
        self, api_client, bk_app, bk_user, another_user, another_user_role, request_user_idx, be_deleted_idx, status
    ):
        G(
            ApplicationMembership,
            application=bk_app,
            user=another_user.pk,
            role=another_user_role.value,
            region=settings.DEFAULT_REGION_NAME,
        )
        user_choices = [bk_user, another_user, create_user("dummy")]
        cur_user = user_choices[request_user_idx]
        user_to_delete = user_choices[be_deleted_idx]

        url = reverse("api.applications.members.detail", kwargs=dict(code=bk_app.code, user_id=user_to_delete.pk))

        api_client.force_authenticate(cur_user)
        response = api_client.delete(url)
        assert response.status_code == status

        if status == 204:
            assert bk_app.applicationmembership_set.count() == 1
        else:
            assert bk_app.applicationmembership_set.count() == 2

    @pytest.mark.parametrize(
        "another_user_role, request_user_idx, status, code",
        [
            (ApplicationRole.ADMINISTRATOR, 0, 400, "MEMBERSHIP_OWNER_FAILED"),
            (ApplicationRole.ADMINISTRATOR, 1, 204, ...),
            (ApplicationRole.DEVELOPER, 1, 204, ...),
            (ApplicationRole.ADMINISTRATOR, 2, 403, "ERROR"),
        ],
    )
    def test_level(self, api_client, bk_app, bk_user, another_user, another_user_role, request_user_idx, status, code):
        G(
            ApplicationMembership,
            application=bk_app,
            user=another_user.pk,
            role=another_user_role.value,
            region=settings.DEFAULT_REGION_NAME,
        )
        user_choices = [bk_user, another_user, create_user("dummy")]
        cur_user = user_choices[request_user_idx]

        url = reverse("api.applications.members.leave", kwargs=dict(code=bk_app.code))
        api_client.force_authenticate(cur_user)
        response = api_client.post(url)
        assert response.status_code == status

        user_count = 1 if status == 204 else 2
        assert bk_app.applicationmembership_set.count() == user_count

        if code is not ...:
            assert response.json()["code"] == code

    def test_level_last_admin(self, api_client, bk_app, bk_user, another_user):
        G(
            ApplicationMembership,
            application=bk_app,
            user=another_user.pk,
            role=ApplicationRole.ADMINISTRATOR.value,
            region=settings.DEFAULT_REGION_NAME,
        )
        ApplicationMembership.objects.filter(application=bk_app, user=bk_user.pk).update(
            role=ApplicationRole.DEVELOPER.value
        )
        cur_user = another_user

        url = reverse("api.applications.members.leave", kwargs=dict(code=bk_app.code))
        api_client.force_authenticate(cur_user)
        response = api_client.post(url)
        assert response.status_code == 400
        assert bk_app.applicationmembership_set.count() == 2
        assert response.json()["code"] == "MEMBERSHIP_DELETE_FAILED"


class TestApplicationCreateWithEngine:
    """Test application creation APIs with engine enabled"""

    @pytest.mark.parametrize(
        'type, desired_type, creation_succeeded',
        [
            ('default', 'default', True),
            ('bk_plugin', 'bk_plugin', True),
            ('engineless_app', 'engineless_app', False),
        ],
    )
    def test_create_different_types(
        self,
        type,
        desired_type,
        creation_succeeded,
        api_client,
        mock_current_engine_client,
        mock_initialize_with_template,
        settings,
        init_tmpls,
    ):
        # Turn on "allow_creation" in bk_plugin configs
        settings.BK_PLUGIN_CONFIG = {'allow_creation': True}
        with mock.patch.object(IntegratedSvnAppRepoConnector, 'sync_templated_sources') as mocked_sync:
            # Mock return value of syncing template
            mocked_sync.return_value = SourceSyncResult(dest_type='mock')

            random_suffix = generate_random_string(length=6)
            response = api_client.post(
                '/api/bkapps/applications/v2/',
                data={
                    'region': settings.DEFAULT_REGION_NAME,
                    'type': type,
                    'code': f'uta-{random_suffix}',
                    'name': f'uta-{random_suffix}',
                    'engine_params': {
                        'source_origin': SourceOrigin.AUTHORIZED_VCS.value,
                        'source_control_type': 'dft_bk_svn',
                        'source_init_template': settings.DUMMY_TEMPLATE_NAME,
                    },
                },
            )
            if creation_succeeded:
                assert response.status_code == 201
                assert response.json()['application']['type'] == desired_type
            else:
                assert response.status_code == 400
                assert response.json()["detail"] == '已开启引擎，类型不能为 "enginess_app"'

    @pytest.mark.parametrize(
        'source_origin, source_repo_url, source_control_type, with_feature_flag, is_success',
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
        mock_current_engine_client,
        source_origin,
        source_repo_url,
        source_control_type,
        with_feature_flag,
        is_success,
        init_tmpls,
    ):
        # Set user feature flag
        AccountFeatureFlag.objects.set_feature(bk_user, AFF.ALLOW_CHOOSE_SOURCE_ORIGIN, with_feature_flag)

        random_suffix = generate_random_string(length=6)
        response = api_client.post(
            '/api/bkapps/applications/v2/',
            data={
                'region': settings.DEFAULT_REGION_NAME,
                'code': f'uta-{random_suffix}',
                'name': f'uta-{random_suffix}',
                'engine_params': {
                    'source_origin': source_origin,
                    'source_repo_url': source_repo_url,
                    'source_init_template': settings.DUMMY_TEMPLATE_NAME,
                    'source_control_type': source_control_type,
                },
            },
        )
        desired_status_code = 201 if is_success else 400
        assert response.status_code == desired_status_code


class TestApplicationCreateWithoutEngine:
    """Test application creation APIs with engine disabled"""

    @pytest.mark.parametrize("url", ['/api/bkapps/applications/v2/', '/api/bkapps/third-party/'])
    def test_create_non_engine(self, api_client, url):
        random_suffix = generate_random_string(length=6)
        response = api_client.post(
            url,
            data={
                'region': settings.DEFAULT_REGION_NAME,
                'code': f'uta-{random_suffix}',
                'name': f'uta-{random_suffix}',
                "engine_enabled": False,
                'market_params': {},
            },
        )
        assert response.status_code == 201
        assert response.json()['application']['type'] == 'engineless_app'

    @pytest.mark.parametrize("url", ['/api/bkapps/applications/v2/', '/api/bkapps/third-party/'])
    @pytest.mark.parametrize(
        'profile_regions,region,creation_success',
        [
            (['r1'], 'r1', True),
            (['r1', 'r2'], 'r1', True),
            (['r1'], 'r2', False),
        ],
    )
    def test_region_permission_control(self, bk_user, api_client, url, profile_regions, region, creation_success):
        """When user has or doesn't have permission, test application creation."""
        with configure_regions(['r1', 'r2']):
            user_profile = UserProfile.objects.get_profile(bk_user)
            user_profile.enable_regions = ';'.join(profile_regions)
            user_profile.save()

            random_suffix = generate_random_string(length=6)
            response = api_client.post(
                url,
                data={
                    'region': region,
                    'code': f'uta-{random_suffix}',
                    'name': f'uta-{random_suffix}',
                    "engine_enabled": False,
                    'market_params': {},
                },
            )
            desired_status_code = 201 if creation_success else 403
            assert response.status_code == desired_status_code


class TestApplicationUpdate:
    """Test update application API"""

    def test_normal(self, api_client, bk_app, bk_user, random_name, mock_current_engine_client):
        response = api_client.put(
            '/api/bkapps/applications/{}/'.format(bk_app.code),
            data={'name': random_name},
        )
        assert response.status_code == 200
        assert Application.objects.get(pk=bk_app.pk).name == random_name

    def test_duplicated(self, api_client, bk_app, bk_user, random_name, mock_current_engine_client):
        G(Application, name=random_name)
        response = api_client.put(
            '/api/bkapps/applications/{}/'.format(bk_app.code),
            data={'name': random_name},
        )
        assert response.status_code == 400
        assert response.json()["code"] == "VALIDATION_ERROR"
        assert f"应用名称 为 {random_name} 的应用已存在" in response.json()["detail"]

    def test_desc_app(self, api_client, bk_user, random_name, mock_current_engine_client):
        get_desc_handler(
            dict(
                spec_version=2,
                app={'bk_app_code': random_name, 'bk_app_name': random_name},
                modules={random_name: {"is_default": True, "language": "python"}},
            )
        ).handle_app(bk_user)
        app = Application.objects.get(code=random_name)
        response = api_client.put(
            '/api/bkapps/applications/{}/'.format(app.code),
            data={'name': random_name},
        )
        assert response.status_code == 400
        assert response.json()['code'] == 'APP_RES_PROTECTED'


class TestApplicationDeletion:
    """Test delete application API"""

    def test_normal(self, api_client, bk_app, bk_user, mock_current_engine_client):
        assert not Operation.objects.filter(application=bk_app, type=OperationType.DELETE_APPLICATION.value).exists()
        response = api_client.delete('/api/bkapps/applications/{}/'.format(bk_app.code))
        assert response.status_code == 204
        assert Operation.objects.filter(application=bk_app, type=OperationType.DELETE_APPLICATION.value).exists()

    def test_rollback(self, api_client, bk_app, bk_user, mock_current_engine_client):
        assert not Operation.objects.filter(application=bk_app, type=OperationType.DELETE_APPLICATION.value).exists()
        with mock.patch(
            "paasng.platform.applications.views.ApplicationViewSet._delete_all_module",
            side_effect=error_codes.CANNOT_DELETE_APP,
        ):
            response = api_client.delete('/api/bkapps/applications/{}/'.format(bk_app.code))
        assert response.status_code == 400
        assert Operation.objects.filter(application=bk_app, type=OperationType.DELETE_APPLICATION.value).exists()


class TestCreateBkPlugin:
    """Test 'bk_plugin' type application's creation"""

    def test_normal(self, api_client, mock_current_engine_client, settings, init_tmpls):
        settings.BK_PLUGIN_CONFIG = {'allow_creation': True}
        response = self._send_creation_request(api_client)

        assert response.status_code == 201, f'error: {response.json()["detail"]}'
        assert response.json()['application']['type'] == 'bk_plugin'
        # TODO: Update tests when bk_plugin supports multiple languages
        assert response.json()['application']['language'] == 'Python'
        assert response.json()['application']['modules'][0]['repo'] is not None

    def test_forbidden_via_config(self, api_client, mock_current_engine_client, settings):
        settings.BK_PLUGIN_CONFIG = {'allow_creation': False}
        response = self._send_creation_request(api_client)

        assert response.status_code == 400, 'the creation of bk_plugin must fail'

    def _send_creation_request(self, api_client):
        random_suffix = generate_random_string(length=6)
        return api_client.post(
            '/api/bkapps/applications/v2/',
            data={
                'region': settings.DEFAULT_REGION_NAME,
                'type': 'bk_plugin',
                'code': f'uta-{random_suffix}',
                'name': f'uta-{random_suffix}',
                'engine_params': {
                    'source_origin': SourceOrigin.AUTHORIZED_VCS.value,
                    'source_control_type': 'dft_gitlab',
                    'source_repo_url': 'http://example.com/default/git.git',
                },
            },
        )


class TestCreateCloudNativeApp:
    """Test 'cloud_native' type application's creation"""

    def test_normal(self, bk_user, api_client, mock_current_engine_client, settings):
        settings.CLOUD_NATIVE_APP_DEFAULT_CLUSTER = "default"
        AccountFeatureFlag.objects.set_feature(bk_user, AFF.ALLOW_CREATE_CLOUD_NATIVE_APP, True)

        random_suffix = generate_random_string(length=6)
        response = api_client.post(
            '/api/bkapps/cloud-native/',
            data={
                'region': settings.DEFAULT_REGION_NAME,
                'code': f'uta-{random_suffix}',
                'name': f'uta-{random_suffix}',
                'cloud_native_params': {
                    'image': 'nginx:alpine',
                },
            },
        )
        assert response.status_code == 201, f'error: {response.json()["detail"]}'
        assert response.json()['application']['type'] == 'cloud_native'
