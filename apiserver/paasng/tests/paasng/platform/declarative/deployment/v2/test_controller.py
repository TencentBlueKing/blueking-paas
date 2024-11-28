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
from django_dynamic_fixture import G

from paasng.platform.applications.models import Application
from paasng.platform.bkapp_model import fieldmgr
from paasng.platform.bkapp_model.entities.hooks import HookCmd, Hooks
from paasng.platform.bkapp_model.entities.svc_discovery import SvcDiscEntryBkSaaS
from paasng.platform.bkapp_model.entities_syncer.hooks import sync_hooks
from paasng.platform.bkapp_model.entities_syncer.svc_discovery import sync_svc_discovery
from paasng.platform.bkapp_model.fieldmgr.constants import FieldMgrName
from paasng.platform.bkapp_model.models import ModuleProcessSpec, SvcDiscConfig, get_svc_disc_as_env_variables
from paasng.platform.declarative.deployment.controller import DeploymentDeclarativeController
from paasng.platform.declarative.deployment.svc_disc import BkSaaSEnvVariableFactory
from paasng.platform.declarative.deployment.validations.v2 import DeploymentDescSLZ
from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.platform.declarative.models import DeploymentDescription
from paasng.platform.declarative.serializers import validate_desc
from paasng.platform.engine.constants import ConfigVarEnvName
from paasng.platform.engine.models.preset_envvars import PresetEnvVariable
from paasng.platform.modules.constants import DeployHookType
from paasng.platform.modules.models.deploy_config import Hook, HookList
from paasng.platform.modules.models.module import Module
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
        print(web.__dict__)
        assert web.get_proc_command() == command
        assert web.command is None
        assert web.args is None


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
        G(Application, code="foo-app")
        app = G(Application, code="bar-app")
        G(Module, name="api", application=app)

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


class TestSvcDiscoveryFieldMultiManagers:
    def test_notset_should_reset(self, bk_app, bk_deployment):
        json_data = {"svc_discovery": {"bk_saas": [{"bk_app_code": bk_app.code}]}, "language": "python"}
        controller = DeploymentDeclarativeController(bk_deployment)
        controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))

        assert len(SvcDiscConfig.objects.get(application=bk_app).bk_saas) == 1

        # Re-apply the data without svc_discovery
        json_data = {"language": "python"}
        controller = DeploymentDeclarativeController(bk_deployment)
        controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))

        assert not SvcDiscConfig.objects.filter(application=bk_app).exists()

    def test_notset_should_skip_when_manager_different(self, bk_app, bk_module, bk_deployment):
        # Insert the data using "web_form" manager
        sync_svc_discovery(
            bk_module,
            SvcDiscConfig(bk_saas=[SvcDiscEntryBkSaaS(bk_app_code=bk_app.code)]),
            fieldmgr.FieldMgrName.WEB_FORM,
        )
        assert len(SvcDiscConfig.objects.get(application=bk_app).bk_saas) == 1

        # Re-apply the data without svc_discovery, the data should stay because it's
        # managed by a different manager.
        json_data = {"language": "python"}
        controller = DeploymentDeclarativeController(bk_deployment)
        controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))

        assert len(SvcDiscConfig.objects.get(application=bk_app).bk_saas) == 1


class TestHookField:
    def test_field_not_set(self, bk_module, bk_deployment):
        controller = DeploymentDeclarativeController(bk_deployment)

        controller.perform_action(desc=validate_desc(DeploymentDescSLZ, {"language": "python"}))

        assert len(bk_deployment.get_deploy_hooks()) == 0
        self.assert_hook_not_exist(bk_module, bk_deployment)

    def test_field_set(self, bk_module, bk_deployment):
        controller = DeploymentDeclarativeController(bk_deployment)
        controller.perform_action(
            desc=validate_desc(
                DeploymentDescSLZ,
                {"language": "python", "scripts": {"pre_release_hook": "echo 1"}},
            )
        )
        self.assert_one_hook_with_command(bk_module, bk_deployment, [], ["echo", "1"])

    @pytest.mark.parametrize("hook_disabled", [True, False])
    def test_not_set_should_not_touch_deployment(self, hook_disabled, bk_module, bk_deployment):
        bk_module.deploy_hooks.enable_hook(DeployHookType.PRE_RELEASE_HOOK, command="echo 1")
        if hook_disabled:
            bk_module.deploy_hooks.disable_hook(DeployHookType.PRE_RELEASE_HOOK)

        controller = DeploymentDeclarativeController(bk_deployment)

        json_data = {"language": "python"}
        controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))

        # The deployment's hook should stay the same
        deploy_hooks = bk_deployment.get_deploy_hooks()
        if hook_disabled:
            assert len(deploy_hooks) == 0
        else:
            assert len(deploy_hooks) == 1
            assert deploy_hooks[0].command == "echo 1"

        desc_obj = DeploymentDescription.objects.get(deployment=bk_deployment)
        assert desc_obj.get_deploy_hooks() == HookList()

    @pytest.mark.parametrize("hook_disabled", [True, False])
    def test_rewrite_the_hook(self, hook_disabled, bk_module, bk_deployment):
        bk_module.deploy_hooks.enable_hook(DeployHookType.PRE_RELEASE_HOOK, command="echo 1")
        if hook_disabled:
            bk_module.deploy_hooks.disable_hook(DeployHookType.PRE_RELEASE_HOOK)

        controller = DeploymentDeclarativeController(bk_deployment)

        json_data = {"language": "python", "scripts": {"pre_release_hook": "echo 2"}}
        controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))

        # The hook should has been modified
        self.assert_one_hook_with_command(bk_module, bk_deployment, [], ["echo", "2"])

    def test_not_set_should_reset(self, bk_module, bk_deployment):
        controller = DeploymentDeclarativeController(bk_deployment)

        controller.perform_action(
            desc=validate_desc(
                DeploymentDescSLZ,
                {"language": "python", "scripts": {"pre_release_hook": "echo 1"}},
            )
        )
        self.assert_one_hook_with_command(bk_module, bk_deployment, [], ["echo", "1"])

        controller.perform_action(desc=validate_desc(DeploymentDescSLZ, {"language": "python"}))
        self.assert_hook_not_exist(bk_module, bk_deployment)

    def test_not_set_with_different_mgr_should_keep(self, bk_module, bk_deployment):
        sync_hooks(
            bk_module,
            Hooks(pre_release=HookCmd(command=["echo"])),
            FieldMgrName.WEB_FORM,
            use_proc_command=True,
        )
        module_hook = bk_module.deploy_hooks.get_by_type(DeployHookType.PRE_RELEASE_HOOK)
        assert module_hook.proc_command == "echo"

        controller = DeploymentDeclarativeController(bk_deployment)
        controller.perform_action(desc=validate_desc(DeploymentDescSLZ, {"language": "python"}))

        # The hook should stay the same because it's managed by a different manager
        module_hook = bk_module.deploy_hooks.get_by_type(DeployHookType.PRE_RELEASE_HOOK)
        assert module_hook.proc_command == "echo"

    # Helper methods start

    def assert_hook_not_exist(self, module, deployment):
        """A helper to assert the hook doesn't exist."""
        desc_obj = DeploymentDescription.objects.get(deployment=deployment)
        assert desc_obj.get_deploy_hooks() == HookList()
        module_hook = module.deploy_hooks.get_by_type(DeployHookType.PRE_RELEASE_HOOK)
        assert module_hook is None

    def assert_one_hook_with_command(self, module, deployment, command, args):
        """A helper to assert there is one hook with the given command."""
        desc_obj = DeploymentDescription.objects.get(deployment=deployment)

        hook_list = HookList([cattr.structure({"type": "pre-release-hook", "command": command, "args": args}, Hook)])
        assert desc_obj.get_deploy_hooks() == hook_list
        assert deployment.get_deploy_hooks() == hook_list

        module_hook = module.deploy_hooks.get_by_type(DeployHookType.PRE_RELEASE_HOOK)
        assert module_hook.command == command
        assert module_hook.args == args
