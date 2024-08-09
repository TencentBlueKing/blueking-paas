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

import cattr
import pytest

from paasng.platform.bkapp_model.models import ModuleProcessSpec, get_svc_disc_as_env_variables
from paasng.platform.declarative.deployment.controller import DeploymentDeclarativeController
from paasng.platform.declarative.deployment.resources import SvcDiscovery
from paasng.platform.declarative.deployment.svc_disc import (
    BkSaaSEnvVariableFactory,
)
from paasng.platform.declarative.deployment.validations.v2 import DeploymentDescSLZ
from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.platform.declarative.models import DeploymentDescription
from paasng.platform.declarative.serializers import validate_desc
from paasng.platform.engine.constants import ConfigVarEnvName
from paasng.platform.engine.models.preset_envvars import PresetEnvVariable
from paasng.platform.modules.constants import DeployHookType
from paasng.platform.modules.models.deploy_config import Hook, HookList
from tests.utils.mocks.cluster import cluster_ingress_config

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestProcessesField:
    def test_python_framework_case(self, bk_module, bk_deployment):
        command = """gunicorn wsgi -w 4 -b [::]:${PORT:-5000} --access-logfile - --error-logfile - --access-logformat '[%(h)s] %({request_id}i)s %(u)s %(t)s "%(r)s" %(s)s %(D)s %(b)s "%(f)s" "%(a)s"'"""
        json_data = {"language": "python", "processes": {"web": {"command": command}}}
        controller = DeploymentDeclarativeController(bk_deployment)
        controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))

        web = ModuleProcessSpec.objects.get(module=bk_module, name="web")
        assert web.get_proc_command() == command

    @pytest.mark.parametrize(
        "command",
        [
            "celery worker -A blueapps.core.celery -P threads -Q er_execute_${BKFLOW_MODULE_CODE} -n er_e_worker@%h -c 100 -l info",
            "go-admin server -c ${HOME}/config/settings.${BKPAAS_ENVIRONMENT}.yml",
            "./group-bot -c app.conf -o console -p $PORT",
            'nginx -g "daemon off;"',
            "celery-prometheus-exporter --broker amqp://$RABBITMQ_USER:$RABBITMQ_PASSWORD@$RABBITMQ_HOST:$RABBITMQ_PORT/$RABBITMQ_VHOST --addr :$PORT --queue-list $CELERY_EXPORTER_QUEUE",
            "python -m gunicorn -w 4 -b [::]:${PORT} 'app:app'",
            "bash -c \"if [[ $(cat config/default.py | grep 'IS_USE_DOCKERFILE' | cut -d'=' -f2) == 'True' ]]; then python manage.py collectstatic --noinput; fi && gunicorn wsgi -w 4 -b :$PORT --access-logfile - --error-logfile - --access-logformat '[%(h)s] %({request_id}i)s %(u)s %(t)s \\\"%(r)s\\\" %(s)s %(D)s %(b)s \\\"%(f)s\\\" \\\"%(a)s\\\"'\"",
        ],
    )
    def test_known_cases(self, bk_module, bk_deployment, command):
        json_data = {"language": "python", "processes": {"web": {"command": command}}}
        controller = DeploymentDeclarativeController(bk_deployment)
        controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))

        web = ModuleProcessSpec.objects.get(module=bk_module, name="web")
        assert web.get_proc_command() == command
        assert web.command is None
        assert web.args is None

    def test_proc_with_no_replicas(self, bk_deployment):
        json_data = {"language": "python", "processes": {"web": {"command": "start"}}}
        controller = DeploymentDeclarativeController(bk_deployment)
        result = controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))

        assert result.loaded_processes["web"].replicas is None

    def test_proc_with_fixed_replicas(self, bk_deployment):
        json_data = {"language": "python", "processes": {"web": {"command": "start", "replicas": 3}}}
        controller = DeploymentDeclarativeController(bk_deployment)
        result = controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))

        assert result.loaded_processes["web"].replicas == 3


class TestEnvVariablesField:
    def test_invalid_input(self, bk_deployment):
        json_data = {"env_variables": "not_a_valid_value"}
        controller = DeploymentDeclarativeController(bk_deployment)
        with pytest.raises(DescriptionValidationError) as exc_info:
            controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))
        assert "env_variables" in str(exc_info.value)

    def test_spec(self, bk_module, bk_deployment):
        json_data = {
            "env_variables": [
                {"key": "FOO", "value": "1"},
                {"key": "BAR", "value": "2"},
            ],
            "language": "python",
        }
        controller = DeploymentDeclarativeController(bk_deployment)
        controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))

        desc_obj = DeploymentDescription.objects.get(deployment=bk_deployment)
        assert len(desc_obj.get_env_variables()) == 2
        assert PresetEnvVariable.objects.filter(module=bk_module).count() == 2

    def test_preset_environ_vars(self, bk_module, bk_deployment):
        json_data = {
            "language": "python",
            "env_variables": [
                {"key": "A", "value": "a"},
                {"key": "A", "value": "a", "environment_name": ConfigVarEnvName.STAG.value},
                {"key": "A", "value": "a", "environment_name": ConfigVarEnvName.PROD.value},
                {"key": "B", "value": "b", "environment_name": ConfigVarEnvName.GLOBAL.value},
            ],
        }
        controller = DeploymentDeclarativeController(bk_deployment)
        controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))

        assert PresetEnvVariable.objects.filter(module=bk_module).count() == 4


class TestSvcDiscoveryField:
    @staticmethod
    def apply_config(bk_deployment):
        json_data = {
            "svc_discovery": {
                "bk_saas": [
                    {"bk_app_code": "foo-app"},
                    {"bk_app_code": "bar-app", "module_name": "api"},
                ]
            },
            "language": "python",
        }
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
        with cluster_ingress_config(replaced_config={"app_root_domains": [{"name": "foo.com"}, {"name": "bar.com"}]}):
            self.apply_config(bk_deployment)
            env_vars = get_svc_disc_as_env_variables(bk_deployment.app_environment)
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
        with cluster_ingress_config(replaced_config={"sub_path_domains": [{"name": "foo.com"}, {"name": "bar.com"}]}):
            self.apply_config(bk_deployment)
            env_vars = get_svc_disc_as_env_variables(bk_deployment.app_environment)
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
            ({"language": "python"}, HookList()),
            (
                {"language": "python", "scripts": {"pre_release_hook": "echo 1;"}},
                HookList([cattr.structure({"type": "pre-release-hook", "command": [], "args": ["echo", "1;"]}, Hook)]),
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
                {"language": "python"},
                HookList([cattr.structure({"type": "pre-release-hook", "command": "echo 1;"}, Hook)]),
            ),
            (
                {"language": "python", "scripts": {"pre_release_hook": "echo 2;"}},
                HookList([cattr.structure({"type": "pre-release-hook", "command": [], "args": ["echo", "2;"]}, Hook)]),
            ),
        ],
    )
    def test_hooks_override(self, bk_deployment, json_data, expected):
        bk_deployment.hooks.upsert(DeployHookType.PRE_RELEASE_HOOK, command="echo 1;")
        bk_deployment.save()

        controller = DeploymentDeclarativeController(bk_deployment)
        controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))

        assert bk_deployment.get_deploy_hooks() == expected

    @pytest.mark.parametrize(
        ("json_data", "expected"),
        [
            ({"language": "python"}, HookList()),
            (
                {"language": "python", "scripts": {"pre_release_hook": "echo 2;"}},
                HookList([cattr.structure({"type": "pre-release-hook", "command": [], "args": ["echo", "2;"]}, Hook)]),
            ),
        ],
    )
    def test_disable_hooks(self, bk_deployment, json_data, expected):
        bk_deployment.hooks.upsert(DeployHookType.PRE_RELEASE_HOOK, command="echo 1;")
        bk_deployment.hooks.disable(DeployHookType.PRE_RELEASE_HOOK)
        bk_deployment.save()

        controller = DeploymentDeclarativeController(bk_deployment)
        controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))
        bk_deployment.refresh_from_db()
        assert bk_deployment.get_deploy_hooks() == expected
