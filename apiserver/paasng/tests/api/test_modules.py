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

import cattr
import pytest
from django.conf import settings

from paasng.accounts.constants import AccountFeatureFlag as AFF
from paasng.accounts.models import AccountFeatureFlag
from paasng.dev_resources.sourcectl.connector import IntegratedSvnAppRepoConnector, SourceSyncResult
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.models.deploy_config import Hook
from paasng.platform.modules.models.module import Module
from paasng.platform.operations.constant import OperationType
from paasng.platform.operations.models import Operation
from tests.utils.helpers import generate_random_string, initialize_module

pytestmark = pytest.mark.django_db


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
        mock_current_engine_client,
        mock_initialize_with_template,
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
        self, api_client, init_tmpls, bk_app, bk_user, mock_current_engine_client, with_feature_flag, is_success
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


class TestModuleDeployConfigViewSet:
    @pytest.fixture
    def the_hook(self, bk_module):
        deploy_config = bk_module.get_deploy_config()
        deploy_config.hooks.upsert("pre-release-hook", "the-hook")
        deploy_config.save()

        return deploy_config.hooks.get_hook("pre-release-hook")

    @pytest.fixture
    def the_procfile(self, bk_module):
        deploy_config = bk_module.get_deploy_config()
        deploy_config.procfile = {"web": "python -m http.server"}
        deploy_config.save()
        return [{"name": "web", "command": "python -m http.server"}]

    def test_retrieve(self, api_client, bk_app, bk_module, the_procfile, the_hook):
        response = api_client.get(f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/deploy_config/")

        assert response.status_code == 200
        assert response.json() == {"procfile": the_procfile, "hooks": [cattr.unstructure(the_hook)]}

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
            assert bk_module.get_deploy_config().hooks.get_hook(type_) == Hook(
                type=type_, command=command, enabled=True
            )
        else:
            assert response.status_code == 400

    def test_disable_hook(self, api_client, bk_app, bk_module, the_hook):
        response = api_client.put(
            f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}"
            f"/deploy_config/hooks/{the_hook.type}/disable/"
        )
        assert response.status_code == 204

        deploy_config = bk_module.get_deploy_config()
        assert deploy_config.hooks.get_hook(the_hook.type) == Hook(
            type=the_hook.type, command=the_hook.command, enabled=False
        )

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

        deploy_config = bk_module.get_deploy_config()
        assert deploy_config.procfile == expected_procfile


class TestModuleDeletion:
    """Test delete module API"""

    def test_delete_main_module(self, api_client, bk_app, bk_module, bk_user, mock_current_engine_client):
        assert not Operation.objects.filter(application=bk_app, type=OperationType.DELETE_MODULE.value).exists()
        response = api_client.delete(f'/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/')
        assert response.status_code == 400
        assert "主模块不允许被删除" in response.json()["detail"]
        assert not Operation.objects.filter(application=bk_app, type=OperationType.DELETE_MODULE.value).exists()

    def test_delete_module(self, api_client, bk_app, bk_user, mock_current_engine_client):
        module = Module.objects.create(application=bk_app, name="test", language="python", source_init_template="test")
        initialize_module(module)

        assert not Operation.objects.filter(application=bk_app, type=OperationType.DELETE_MODULE.value).exists()
        response = api_client.delete(f'/api/bkapps/applications/{bk_app.code}/modules/{module.name}/')
        assert response.status_code == 204
        assert Operation.objects.filter(application=bk_app, type=OperationType.DELETE_MODULE.value).exists()

    def test_delete_rollback(self, api_client, bk_app, bk_user, mock_current_engine_client):
        module = Module.objects.create(application=bk_app, name="test", language="python", source_init_template="test")
        initialize_module(module)

        assert not Operation.objects.filter(application=bk_app, type=OperationType.DELETE_MODULE.value).exists()
        with mock.patch("paasng.platform.modules.views.delete_module", side_effect=Exception):
            response = api_client.delete(f'/api/bkapps/applications/{bk_app.code}/modules/{module.name}/')
        assert response.status_code == 400
        assert Operation.objects.filter(application=bk_app, type=OperationType.DELETE_MODULE.value).exists()
