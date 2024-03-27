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

from paasng.platform.bkapp_model.models import ModuleProcessSpec
from paasng.platform.declarative.deployment.controller import DeploymentDeclarativeController
from paasng.platform.declarative.deployment.env_vars import EnvVariablesReader
from paasng.platform.declarative.deployment.resources import SvcDiscovery
from paasng.platform.declarative.deployment.svc_disc import (
    BkSaaSEnvVariableFactory,
    get_services_as_env_variables,
)
from paasng.platform.declarative.deployment.validations.v3 import DeploymentDescSLZ
from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.platform.declarative.models import DeploymentDescription
from paasng.platform.declarative.serializers import validate_desc
from paasng.platform.modules.constants import DeployHookType
from paasng.platform.modules.models.deploy_config import Hook, HookList
from tests.paasng.platform.declarative.utils import AppDescV3Builder as builder  # noqa: N813
from tests.utils.mocks.engine import mock_cluster_service

pytestmark = pytest.mark.django_db


class TestProcessesField:
    def test_python_framework_case(self, bk_module, bk_deployment):
        json_data = builder.make_module(
            module_name="test",
            module_spec={
                "processes": [
                    {
                        "name": "web",
                        "command": ["gunicorn"],
                        "args": [
                            "wsgi",
                            "-w",
                            "4",
                            "-b",
                            "[::]:${PORT:-5000}",
                            "--access-logfile",
                            "-",
                            "--error-logfile",
                            "-",
                            "--access-logformat",
                            '[%(h)s] %({request_id}i)s %(u)s %(t)s "%(r)s" %(s)s %(D)s %(b)s "%(f)s" "%(a)s"',
                        ],
                        "replicas": 1,
                    }
                ]
            },
        )

        controller = DeploymentDeclarativeController(bk_deployment)
        controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))

        web = ModuleProcessSpec.objects.get(module=bk_module, name="web")
        assert (
            web.get_proc_command()
            == 'gunicorn wsgi -w 4 -b [::]:${PORT} --access-logfile - --error-logfile - --access-logformat \'[%(h)s] %({request_id}i)s %(u)s %(t)s "%(r)s" %(s)s %(D)s %(b)s "%(f)s" "%(a)s"\''
        )
        assert (
            bk_deployment.declarative_config.spec.processes[0].get_proc_command()
            == 'bash -c \'"$(eval echo \\"$0\\")" "$(eval echo \\"${1}\\")" "$(eval echo \\"${2}\\")" "$(eval echo \\"${3}\\")" "$(eval echo \\"${4}\\")" "$(eval echo \\"${5}\\")" "$(eval echo \\"${6}\\")" "$(eval echo \\"${7}\\")" "$(eval echo \\"${8}\\")" "$(eval echo \\"${9}\\")" "$(eval echo \\"${10}\\")" "$(eval echo \\"${11}\\")"\' gunicorn wsgi -w 4 -b \'[::]:${PORT:-5000}\' --access-logfile - --error-logfile - --access-logformat \'[%(h)s] %({request_id}i)s %(u)s %(t)s "%(r)s" %(s)s %(D)s %(b)s "%(f)s" "%(a)s"\''
        )


class TestEnvVariablesField:
    def test_invalid_input(self, bk_deployment):
        json_data = builder.make_module(
            module_name="test",
            module_spec={
                "configuration": {"env": ""},
                "envOverlay": {
                    "envVariables": [
                        {"name": "BAZ", "value": "stag", "envName": "stag"},
                        {"name": "BAZ", "value": "prod", "envName": "prod"},
                    ]
                },
            },
        )
        controller = DeploymentDeclarativeController(bk_deployment)
        with pytest.raises(DescriptionValidationError, match="spec: configuration -> env"):
            controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))

    def test_spec(self, bk_deployment):
        json_data = builder.make_module(
            module_name="test",
            module_spec={
                "configuration": {"env": [{"name": "FOO", "value": "1"}, {"name": "BAR", "value": "2"}]},
                "envOverlay": {
                    "envVariables": [
                        {"name": "BAZ", "value": "stag", "envName": "stag"},
                        {"name": "BAZ", "value": "prod", "envName": "prod"},
                    ]
                },
            },
        )
        controller = DeploymentDeclarativeController(bk_deployment)
        controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))

        desc_obj = DeploymentDescription.objects.get(deployment=bk_deployment)
        assert len(desc_obj.get_env_variables()) == 3


class TestEnvVariablesReader:
    @pytest.fixture(autouse=True)
    def _setup_tasks(self, bk_user, bk_deployment):
        json_data = builder.make_module(
            module_name="test",
            module_spec={
                "configuration": {"env": [{"name": "FOO", "value": "1"}, {"name": "BAR", "value": "2"}]},
                "envOverlay": {
                    "envVariables": [
                        {"name": "STAG", "value": "3", "envName": "stag"},
                        {"name": "PROD", "value": "4", "envName": "prod"},
                    ]
                },
            },
        )
        controller = DeploymentDeclarativeController(bk_deployment)
        controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))

    def test_read_as_dict(self, bk_deployment):
        desc_obj = DeploymentDescription.objects.get(deployment=bk_deployment)
        assert EnvVariablesReader(desc_obj).read_as_dict() == {"FOO": "1", "BAR": "2", "PROD": "4"}


class TestSvcDiscoveryField:
    @staticmethod
    def apply_config(bk_deployment):
        json_data = builder.make_module(
            module_name="test",
            module_spec={
                "svcDiscovery": {"bkSaaS": [{"bkAppCode": "foo-app"}, {"bkAppCode": "bar-app", "moduleName": "api"}]}
            },
        )
        controller = DeploymentDeclarativeController(bk_deployment)
        controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))

    def test_store(self, bk_deployment):
        self.apply_config(bk_deployment)
        desc_obj = DeploymentDescription.objects.get(deployment=bk_deployment)

        assert desc_obj.get_svc_discovery() == cattr.structure(
            {
                "bk_saas": [
                    {"bk_app_code": "foo-app", "module_name": None},
                    {"bk_app_code": "bar-app", "module_name": "api"},
                ]
            },
            SvcDiscovery,
        )

    def test_as_env_vars_domain(self, bk_deployment):
        with mock_cluster_service(
            replaced_ingress_config={"app_root_domains": [{"name": "foo.com"}, {"name": "bar.com"}]}
        ):
            self.apply_config(bk_deployment)
            env_vars = get_services_as_env_variables(bk_deployment)
            value = env_vars["BKPAAS_SERVICE_ADDRESSES_BKSAAS"]
            addresses = BkSaaSEnvVariableFactory.decode_data(value)
            assert len(addresses) == 2
            assert addresses[0]["key"] == {"bk_app_code": "foo-app", "module_name": None}
            assert addresses[0]["value"] == {
                "stag": "http://stag-dot-foo-app.foo.com",
                "prod": "http://foo-app.foo.com",
            }

            assert addresses[1]["key"] == {"bk_app_code": "bar-app", "module_name": "api"}
            assert addresses[1]["value"] == {
                "stag": "http://stag-dot-api-dot-bar-app.foo.com",
                "prod": "http://prod-dot-api-dot-bar-app.foo.com",
            }

    def test_as_env_vars_subpath(self, bk_deployment):
        with mock_cluster_service(
            replaced_ingress_config={"sub_path_domains": [{"name": "foo.com"}, {"name": "bar.com"}]}
        ):
            self.apply_config(bk_deployment)
            env_vars = get_services_as_env_variables(bk_deployment)
            value = env_vars["BKPAAS_SERVICE_ADDRESSES_BKSAAS"]
            addresses = BkSaaSEnvVariableFactory.decode_data(value)
            assert len(addresses) == 2
            assert addresses[0]["key"] == {"bk_app_code": "foo-app", "module_name": None}
            assert addresses[0]["value"] == {
                "stag": "http://foo.com/stag--foo-app/",
                "prod": "http://foo.com/foo-app/",
            }

            assert addresses[1]["key"] == {"bk_app_code": "bar-app", "module_name": "api"}
            assert addresses[1]["value"] == {
                "stag": "http://foo.com/stag--api--bar-app/",
                "prod": "http://foo.com/prod--api--bar-app/",
            }


class TestHookField:
    @pytest.mark.parametrize(
        ("json_data", "expected"),
        [
            (builder.make_module(module_name="test"), HookList()),
            (
                builder.make_module(
                    module_name="test",
                    module_spec={"hooks": {"preRelease": {"command": [], "args": ["echo", "1"]}}},
                ),
                HookList([cattr.structure({"type": "pre-release-hook", "command": [], "args": ["echo", "1"]}, Hook)]),
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
        ("json_data", "expected"),
        [
            (
                builder.make_module(module_name="test"),
                HookList([cattr.structure({"type": "pre-release-hook", "command": [], "args": ["echo", "1"]}, Hook)]),
            ),
            (
                builder.make_module(
                    module_name="test",
                    module_spec={"hooks": {"preRelease": {"command": [], "args": ["echo", "2"]}}},
                ),
                HookList([cattr.structure({"type": "pre-release-hook", "command": [], "args": ["echo", "2"]}, Hook)]),
            ),
        ],
    )
    def test_hooks_override(self, bk_deployment, json_data, expected):
        bk_deployment.hooks.upsert(DeployHookType.PRE_RELEASE_HOOK, command=[], args=["echo", "1"])
        bk_deployment.save()

        controller = DeploymentDeclarativeController(bk_deployment)
        controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))

        assert bk_deployment.get_deploy_hooks() == expected

    @pytest.mark.parametrize(
        ("json_data", "expected"),
        [
            (
                builder.make_module(module_name="test"),
                HookList(),
            ),
            (
                builder.make_module(
                    module_name="test",
                    module_spec={"hooks": {"preRelease": {"command": [], "args": ["echo", "2"]}}},
                ),
                HookList([cattr.structure({"type": "pre-release-hook", "command": [], "args": ["echo", "2"]}, Hook)]),
            ),
        ],
    )
    def test_disable_hooks(self, bk_deployment, json_data, expected):
        bk_deployment.hooks.upsert(DeployHookType.PRE_RELEASE_HOOK, command=[], args=["echo", "1"])
        bk_deployment.hooks.disable(DeployHookType.PRE_RELEASE_HOOK)
        bk_deployment.save()

        controller = DeploymentDeclarativeController(bk_deployment)
        controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))
        bk_deployment.refresh_from_db()
        assert bk_deployment.get_deploy_hooks() == expected
