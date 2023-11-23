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

from paasng.infras.accounts.constants import AccountFeatureFlag as AFF
from paasng.infras.accounts.models import AccountFeatureFlag
from paasng.misc.operations.constant import OperationType
from paasng.misc.operations.models import Operation
from paasng.platform.bkapp_model.models import ModuleProcessSpec
from paasng.platform.modules.constants import DeployHookType, SourceOrigin
from paasng.platform.modules.models import BuildConfig
from paasng.platform.modules.models.module import Module
from paasng.platform.sourcectl.connector import IntegratedSvnAppRepoConnector, SourceSyncResult
from tests.conftest import CLUSTER_NAME_FOR_TESTING
from tests.utils.helpers import generate_random_string, initialize_module

pytestmark = pytest.mark.django_db(databases=['default', 'workloads'])


logger = logging.getLogger(__name__)


class TestModuleCreation:
    """Test module creation APIs"""

    @pytest.mark.parametrize(
        'creation_params',
        [
            {
                'source_origin': SourceOrigin.AUTHORIZED_VCS.value,
                'source_control_type': 'dft_bk_svn',
            },
            {
                'source_origin': SourceOrigin.IMAGE_REGISTRY.value,
                'source_control_type': 'dft_docker',
                'source_repo_url': '127.0.0.1:5000/library/python',
            },
        ],
    )
    def test_create_different_engine_params(
        self,
        api_client,
        init_tmpls,
        bk_app,
        mock_wl_services_in_creation,
        mock_initialize_vcs_with_template,
        creation_params,
    ):
        with mock.patch.object(IntegratedSvnAppRepoConnector, 'sync_templated_sources') as mocked_sync:
            # Mock return value of syncing template
            mocked_sync.return_value = SourceSyncResult(dest_type='mock')

            random_suffix = generate_random_string(length=6)
            response = api_client.post(
                f'/api/bkapps/applications/{bk_app.code}/modules/',
                data={
                    'name': f'uta-{random_suffix}',
                    'source_init_template': settings.DUMMY_TEMPLATE_NAME,
                    **creation_params,
                },
            )
            assert response.status_code == 201

    @pytest.mark.parametrize('with_feature_flag,is_success', [(True, True), (False, False)])
    def test_create_nondefault_origin(
        self,
        api_client,
        init_tmpls,
        bk_app,
        bk_user,
        mock_wl_services_in_creation,
        with_feature_flag,
        is_success,
    ):
        # Set user feature flag
        AccountFeatureFlag.objects.set_feature(bk_user, AFF.ALLOW_CHOOSE_SOURCE_ORIGIN, with_feature_flag)

        with mock.patch.object(IntegratedSvnAppRepoConnector, 'sync_templated_sources') as mocked_sync:
            # Mock return value of syncing template
            mocked_sync.return_value = SourceSyncResult(dest_type='mock')

            random_suffix = generate_random_string(length=6)
            response = api_client.post(
                f'/api/bkapps/applications/{bk_app.code}/modules/',
                data={
                    'name': f'uta-{random_suffix}',
                    'source_init_template': settings.DUMMY_TEMPLATE_NAME,
                    'source_origin': SourceOrigin.BK_LESS_CODE.value,
                },
            )
            desired_status_code = 201 if is_success else 400
            assert response.status_code == desired_status_code


class TestCreateCloudNativeModule:
    @pytest.fixture(autouse=True)
    def setup(self, mock_wl_services_in_creation, mock_initialize_vcs_with_template, init_tmpls, bk_user, settings):
        settings.CLOUD_NATIVE_APP_DEFAULT_CLUSTER = CLUSTER_NAME_FOR_TESTING
        AccountFeatureFlag.objects.set_feature(bk_user, AFF.ALLOW_CREATE_CLOUD_NATIVE_APP, True)

    def test_create_with_image(self, bk_cnative_app, api_client):
        """托管方式：仅镜像"""
        random_suffix = generate_random_string(length=6)
        image_repository = "strm/helloworld-http"
        response = api_client.post(
            f"/api/bkapps/cloud-native/{bk_cnative_app.code}/modules/",
            data={
                "name": f'uta-{random_suffix}',
                "source_config": {
                    "source_origin": SourceOrigin.CNATIVE_IMAGE,
                    "source_repo_url": "strm/helloworld-http",
                },
                "bkapp_spec": {
                    "build_config": {"build_method": "custom_image", "image_repository": image_repository},
                    "processes": [
                        {
                            "name": "web",
                            "command": ["bash", "/app/start_web.sh"],
                            "env_overlay": {
                                'stag': {'environment_name': 'stag', 'target_replicas': 1, 'plan_name': '2C1G'},
                                'prod': {'environment_name': 'prod', 'target_replicas': 2, 'plan_name': '2C1G'},
                            },
                        }
                    ],
                },
            },
        )
        assert response.status_code == 201, f'error: {response.json()["detail"]}'
        module_data = response.json()['module']
        assert module_data['web_config']['build_method'] == 'custom_image'
        assert module_data['web_config']['artifact_type'] == 'none'
        module = Module.objects.get(id=module_data['id'])
        cfg = BuildConfig.objects.get_or_create_by_module(module)
        assert cfg.image_repository == image_repository
        process_spec = ModuleProcessSpec.objects.get(module=module, name='web')
        assert process_spec.image is None
        assert process_spec.image_credential_name is None
        assert process_spec.command == ["bash", "/app/start_web.sh"]
        assert process_spec.get_target_replicas('stag') == 1
        assert process_spec.get_target_replicas('prod') == 2

    @mock.patch('paasng.platform.modules.helpers.ModuleRuntimeBinder')
    @mock.patch('paasng.platform.engine.configurations.building.ModuleRuntimeManager')
    def test_create_with_buildpack(
        self, MockedModuleRuntimeBinder, MockedModuleRuntimeManager, api_client, bk_cnative_app, init_tmpls
    ):
        """托管方式：源码 & 镜像（使用 buildpack 进行构建）"""
        MockedModuleRuntimeBinder().bind_bp_stack.return_value = None
        MockedModuleRuntimeManager().get_slug_builder.return_value = mock.MagicMock(
            is_cnb_runtime=True, environments={}
        )

        random_suffix = generate_random_string(length=6)
        response = api_client.post(
            f"/api/bkapps/cloud-native/{bk_cnative_app.code}/modules/",
            data={
                "name": f'uta-{random_suffix}',
                'bkapp_spec': {"build_config": {"build_method": "buildpack"}},
                "source_config": {
                    "source_init_template": settings.DUMMY_TEMPLATE_NAME,
                    "source_origin": SourceOrigin.AUTHORIZED_VCS,
                    "source_repo_url": "https://github.com/octocat/helloWorld.git",
                    "source_repo_auth_info": {},
                },
            },
        )
        assert response.status_code == 201, f'error: {response.json()["detail"]}'
        module_data = response.json()['module']
        assert module_data['web_config']['build_method'] == 'buildpack'
        assert module_data['web_config']['artifact_type'] == 'image'

    def test_create_with_dockerfile(self, api_client, bk_cnative_app, init_tmpls):
        """托管方式：源码 & 镜像（使用 dockerfile 进行构建）"""
        random_suffix = generate_random_string(length=6)
        response = api_client.post(
            f"/api/bkapps/cloud-native/{bk_cnative_app.code}/modules/",
            data={
                "name": f'uta-{random_suffix}',
                "bkapp_spec": {
                    "build_config": {
                        "build_method": "dockerfile",
                        'dockerfile_path': 'Dockerfile',
                    }
                },
                "source_config": {
                    "source_init_template": "docker",
                    "source_origin": SourceOrigin.AUTHORIZED_VCS,
                    "source_repo_url": "https://github.com/octocat/helloWorld.git",
                    "source_repo_auth_info": {},
                },
            },
        )
        assert response.status_code == 201, f'error: {response.json()["detail"]}'
        module_data = response.json()['module']
        assert module_data['web_config']['build_method'] == 'dockerfile'
        assert module_data['web_config']['artifact_type'] == 'image'


class TestModuleDeployConfigViewSet:
    @pytest.fixture
    def the_hook(self, bk_module):
        return bk_module.deploy_hooks.enable_hook(type_=DeployHookType.PRE_RELEASE_HOOK, proc_command="the-hook")

    @pytest.fixture
    def the_procfile(self, bk_module):
        ModuleProcessSpec.objects.update_or_create(module=bk_module, name="web", proc_command="python -m http.server")
        return [{"name": "web", "command": "python -m http.server"}]

    def test_retrieve(self, api_client, bk_app, bk_module, the_procfile, the_hook):
        response = api_client.get(f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/deploy_config/")

        assert response.status_code == 200
        assert response.json() == {
            "procfile": the_procfile,
            "hooks": [{"type": the_hook.type, "command": the_hook.proc_command, "enabled": the_hook.enabled}],
        }

    @pytest.mark.parametrize(
        "type_, command, success",
        [
            ("A", "B", False),
            ("pre-release-hook", "B", True),
            ("pre-release-hook", "start a", False),
        ],
    )
    def test_upsert_hook(self, api_client, bk_app, bk_module, type_, command, success):
        response = api_client.post(
            f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/deploy_config/hooks/",
            data={
                "type": type_,
                "command": command,
            },
        )
        if success:
            hook = bk_module.deploy_hooks.get_by_type(type_)
            assert hook.proc_command == command
            assert hook.enabled
        else:
            assert response.status_code == 400

    def test_disable_hook(self, api_client, bk_app, bk_module, the_hook):
        response = api_client.put(
            f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}"
            f"/deploy_config/hooks/{the_hook.type}/disable/"
        )
        assert response.status_code == 204

        hook = bk_module.deploy_hooks.get_by_type(DeployHookType.PRE_RELEASE_HOOK)
        assert hook.proc_command == the_hook.proc_command
        assert not hook.enabled

    @pytest.mark.parametrize(
        "procfile, expected_procfile, success",
        [
            ([], {}, True),
            ([{"name": "web", "command": "python -m http.server"}], {"web": "python -m http.server"}, True),
            ([{"name": "WEB", "command": "python -m http.server"}], {"web": "python -m http.server"}, True),
            ([{"name": "w-e-b", "command": "python -m http.server"}], {"w-e-b": "python -m http.server"}, True),
            ([{"name": "-w-e-b", "command": "python -m http.server"}], {}, False),
            ([{"name": "w" * 13, "command": "python -m http.server"}], {}, False),
        ],
    )
    def test_update_procfile(self, api_client, bk_app, bk_module, procfile, expected_procfile, success):
        bk_module.source_origin = SourceOrigin.IMAGE_REGISTRY
        bk_module.save()

        response = api_client.post(
            f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/deploy_config/procfile/",
            data={"procfile": procfile},
        )

        if success:
            assert response.status_code == 200
        else:
            assert response.status_code == 400

        assert {
            proc.name: proc.get_proc_command() for proc in ModuleProcessSpec.objects.filter(module=bk_module)
        } == expected_procfile


class TestModuleDeletion:
    """Test delete module API"""

    @pytest.fixture(autouse=True)
    def mock_validate_custom_domain(self):
        with mock.patch("paasng.platform.modules.protections.CustomDomainUnBoundCondition.validate"):
            yield

    def test_delete_main_module(self, api_client, bk_app, bk_module, bk_user):
        assert not Operation.objects.filter(application=bk_app, type=OperationType.DELETE_MODULE.value).exists()
        response = api_client.delete(f'/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/')
        assert response.status_code == 400
        assert "主模块不允许被删除" in response.json()["detail"]
        assert not Operation.objects.filter(application=bk_app, type=OperationType.DELETE_MODULE.value).exists()

    def test_delete_module(
        self,
        api_client,
        bk_app,
        bk_user,
        mock_wl_services_in_creation,
    ):
        module = Module.objects.create(application=bk_app, name="test", language="python", source_init_template="test")
        initialize_module(module)

        assert not Operation.objects.filter(application=bk_app, type=OperationType.DELETE_MODULE.value).exists()
        with mock.patch("paasng.platform.modules.manager.delete_module_related_res"):
            response = api_client.delete(f'/api/bkapps/applications/{bk_app.code}/modules/{module.name}/')
        assert response.status_code == 204
        assert Operation.objects.filter(application=bk_app, type=OperationType.DELETE_MODULE.value).exists()

    def test_delete_rollback(self, api_client, bk_app, bk_user):
        module = Module.objects.create(application=bk_app, name="test", language="python", source_init_template="test")
        initialize_module(module)

        assert not Operation.objects.filter(application=bk_app, type=OperationType.DELETE_MODULE.value).exists()
        with mock.patch("paasng.platform.modules.views.delete_module", side_effect=Exception):
            response = api_client.delete(f'/api/bkapps/applications/{bk_app.code}/modules/{module.name}/')
        assert response.status_code == 400
        assert Operation.objects.filter(application=bk_app, type=OperationType.DELETE_MODULE.value).exists()
