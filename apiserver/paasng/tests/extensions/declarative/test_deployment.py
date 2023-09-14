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
import cattr
import pytest

from paasng.extensions.declarative.deployment.controller import DeploymentDeclarativeController
from paasng.extensions.declarative.deployment.env_vars import EnvVariablesReader
from paasng.extensions.declarative.deployment.resources import BkSaaSItem
from paasng.extensions.declarative.deployment.svc_disc import (
    BkSaaSAddrDiscoverer,
    BkSaaSEnvVariableFactory,
    get_services_as_env_variables,
)
from paasng.extensions.declarative.deployment.validations import DeploymentDescSLZ
from paasng.extensions.declarative.exceptions import DescriptionValidationError
from paasng.extensions.declarative.models import DeploymentDescription
from paasng.extensions.declarative.serializers import validate_desc
from paasng.platform.modules.constants import DeployHookType
from paasng.platform.modules.models.deploy_config import Hook, HookList
from tests.utils.mocks.engine import mock_cluster_service

pytestmark = pytest.mark.django_db


@pytest.mark.django_db(databases=["default", "workloads"])
class TestEnvVariablesField:
    def test_invalid_input(self, bk_deployment):
        json_data = {'env_variables': 'not_a_valid_value'}
        controller = DeploymentDeclarativeController(bk_deployment)
        with pytest.raises(DescriptionValidationError) as exc_info:
            controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))
        assert 'env_variables' in str(exc_info.value)

    def test_normal(self, bk_deployment):
        json_data = {
            'env_variables': [
                {'key': 'FOO', 'value': '1'},
                {'key': 'BAR', 'value': '2'},
            ],
            'language': 'python',
        }
        controller = DeploymentDeclarativeController(bk_deployment)
        controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))

        desc_obj = DeploymentDescription.objects.get(deployment=bk_deployment)
        assert len(desc_obj.env_variables) == 2


@pytest.mark.django_db(databases=["default", "workloads"])
class TestEnvVariablesReader:
    @pytest.fixture(autouse=True)
    def setup_tasks(self, bk_user, bk_deployment):
        json_data = {
            'env_variables': [
                {'key': 'FOO', 'value': '1'},
                {'key': 'BAR', 'value': '2'},
                {'key': 'STAG', 'value': '3', 'environment_name': 'stag'},
                {'key': 'PROD', 'value': '4', 'environment_name': 'prod'},
            ],
            'language': 'python',
        }
        controller = DeploymentDeclarativeController(bk_deployment)
        controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))

    def test_read_as_dict(self, bk_deployment):
        desc_obj = DeploymentDescription.objects.get(deployment=bk_deployment)
        assert EnvVariablesReader(desc_obj).read_as_dict() == {'FOO': '1', 'BAR': '2', 'PROD': '4'}


@pytest.mark.django_db(databases=["default", "workloads"])
class TestSvcDiscoveryField:
    @staticmethod
    def apply_config(bk_deployment):
        json_data = {
            'svc_discovery': {
                'bk_saas': [
                    {'bk_app_code': 'foo-app'},
                    {'bk_app_code': 'bar-app', 'module_name': 'api'},
                ]
            },
            'language': 'python',
        }
        controller = DeploymentDeclarativeController(bk_deployment)
        controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))

    def test_store(self, bk_deployment):
        self.apply_config(bk_deployment)
        desc_obj = DeploymentDescription.objects.get(deployment=bk_deployment)
        assert desc_obj.runtime['svc_discovery'] == {
            'bk_saas': [
                {'bk_app_code': 'foo-app', 'module_name': None},
                {'bk_app_code': 'bar-app', 'module_name': 'api'},
            ]
        }

    def test_as_env_vars_domain(self, bk_deployment):
        with mock_cluster_service(
            replaced_ingress_config={'app_root_domains': [{"name": 'foo.com'}, {"name": 'bar.com'}]}
        ):
            self.apply_config(bk_deployment)
            env_vars = get_services_as_env_variables(bk_deployment)
            value = env_vars['BKPAAS_SERVICE_ADDRESSES_BKSAAS']
            addresses = BkSaaSEnvVariableFactory.decode_data(value)
            assert len(addresses) == 2
            assert addresses[0]['key'] == {'bk_app_code': 'foo-app', 'module_name': None}
            assert addresses[0]['value'] == {
                'stag': 'http://stag-dot-foo-app.foo.com',
                'prod': 'http://foo-app.foo.com',
            }

            assert addresses[1]['key'] == {'bk_app_code': 'bar-app', 'module_name': 'api'}
            assert addresses[1]['value'] == {
                'stag': 'http://stag-dot-api-dot-bar-app.foo.com',
                'prod': 'http://prod-dot-api-dot-bar-app.foo.com',
            }

    def test_as_env_vars_subpath(self, bk_deployment):
        with mock_cluster_service(
            replaced_ingress_config={'sub_path_domains': [{"name": 'foo.com'}, {"name": 'bar.com'}]}
        ):
            self.apply_config(bk_deployment)
            env_vars = get_services_as_env_variables(bk_deployment)
            value = env_vars['BKPAAS_SERVICE_ADDRESSES_BKSAAS']
            addresses = BkSaaSEnvVariableFactory.decode_data(value)
            assert len(addresses) == 2
            assert addresses[0]['key'] == {'bk_app_code': 'foo-app', 'module_name': None}
            assert addresses[0]['value'] == {
                'stag': 'http://foo.com/stag--foo-app/',
                'prod': 'http://foo.com/foo-app/',
            }

            assert addresses[1]['key'] == {'bk_app_code': 'bar-app', 'module_name': 'api'}
            assert addresses[1]['value'] == {
                'stag': 'http://foo.com/stag--api--bar-app/',
                'prod': 'http://foo.com/prod--api--bar-app/',
            }


@pytest.mark.django_db(databases=["default", "workloads"])
class TestHookField:
    @pytest.mark.parametrize(
        "json_data, expected",
        [
            ({'language': 'python'}, HookList()),
            (
                {'language': 'python', 'scripts': {'pre_release_hook': 'echo 1;'}},
                HookList([cattr.structure({"type": "pre-release-hook", "command": "echo 1;"}, Hook)]),
            ),
        ],
    )
    def test_hooks(self, bk_deployment, json_data, expected):
        controller = DeploymentDeclarativeController(bk_deployment)
        controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))

        desc_obj = DeploymentDescription.objects.get(deployment=bk_deployment)
        assert desc_obj.get_deploy_hooks() == expected
        assert bk_deployment.get_deploy_hooks() == expected

    @pytest.mark.parametrize(
        "json_data, expected",
        [
            ({'language': 'python'}, HookList()),
            (
                {'language': 'python', 'scripts': {'pre_release_hook': 'echo 2;'}},
                HookList([cattr.structure({"type": "pre-release-hook", "command": "echo 2;"}, Hook)]),
            ),
        ],
    )
    def test_disable_hooks(self, bk_deployment, json_data, expected):
        bk_deployment.hooks.upsert(DeployHookType.PRE_RELEASE_HOOK, "echo 1;")
        bk_deployment.hooks.disable(DeployHookType.PRE_RELEASE_HOOK)
        bk_deployment.save()

        controller = DeploymentDeclarativeController(bk_deployment)
        controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))
        assert bk_deployment.get_deploy_hooks() == expected


class TestBkSaaSEnvVariableFactoryExtendWithClusterApp:
    def test_missing_app(self):
        items = [
            BkSaaSItem(bk_app_code='foo-app'),
            BkSaaSItem(bk_app_code='foo-app', module_name='bar-module'),
        ]
        # clusters 类型为 Dict，这里直接判断是否为空
        cluster_states = [bool(clusters) for _, clusters in BkSaaSAddrDiscoverer.extend_with_clusters(items)]
        # App which is not existed in the database should not has any cluster
        # object returned.
        assert cluster_states == [False, False]

    def test_existed_app(self, bk_app, bk_module):
        items = [
            BkSaaSItem(bk_app_code=bk_app.code),
            BkSaaSItem(bk_app_code=bk_app.code, module_name=bk_module.name),
            BkSaaSItem(bk_app_code=bk_app.code, module_name='wrong-name'),
        ]
        cluster_states = [bool(clusters) for _, clusters in BkSaaSAddrDiscoverer.extend_with_clusters(items)]
        # Item which did not specify module_name and specified a right module name
        # should has a cluster object returned.
        assert cluster_states == [True, True, False]
