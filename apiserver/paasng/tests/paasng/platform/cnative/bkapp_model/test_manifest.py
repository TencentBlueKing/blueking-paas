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
from unittest import mock

import pytest
from django.conf import settings
from django_dynamic_fixture import G

from paas_wl.bk_app.cnative.specs.constants import LEGACY_PROC_IMAGE_ANNO_KEY, ApiVersion, ResQuotaPlan
from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppResource, BkAppSpec, EnvVar, EnvVarOverlay, ObjectMetadata
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.services.models import Plan, Service, ServiceCategory
from paasng.platform.bkapp_model.manifest import (
    DEFAULT_SLUG_RUNNER_ENTRYPOINT,
    AddonsManifestConstructor,
    EnvVarsManifestConstructor,
    ProcessesManifestConstructor,
    get_manifest,
)
from paasng.platform.bkapp_model.models import ModuleProcessSpec
from paasng.platform.engine.constants import RuntimeType
from paasng.platform.engine.models.config_var import ENVIRONMENT_ID_FOR_GLOBAL, ConfigVar
from paasng.platform.modules.models import BuildConfig
from tests.utils.helpers import generate_random_string

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture
def blank_resource() -> BkAppResource:
    """A blank resource object."""
    return BkAppResource(
        apiVersion=ApiVersion.V1ALPHA2, metadata=ObjectMetadata(name='a-blank-resource'), spec=BkAppSpec()
    )


@pytest.fixture
def local_service(bk_app):
    """A local service object."""
    service = G(Service, name='mysql', category=G(ServiceCategory), region=bk_app.region, logo_b64="dummy")
    _ = G(Plan, name=generate_random_string(), service=service)
    return mixed_service_mgr.get(service.uuid, region=bk_app.region)


@pytest.fixture
def process_web(bk_module) -> ModuleProcessSpec:
    """ProcessSpec for web"""
    return G(
        ModuleProcessSpec, module=bk_module, name="web", proc_command="python -m http.server", port=8000, image=None
    )


class TestAddonsManifestConstructor:
    def test_empty(self, bk_module, blank_resource):
        AddonsManifestConstructor().apply_to(blank_resource, bk_module)

        annots = blank_resource.metadata.annotations
        assert annots['bkapp.paas.bk.tencent.com/addons'] == '[]'
        assert len(blank_resource.spec.addons) == 0

    def test_with_addons(self, bk_module, blank_resource, local_service):
        mixed_service_mgr.bind_service(local_service, bk_module)
        AddonsManifestConstructor().apply_to(blank_resource, bk_module)

        annots = blank_resource.metadata.annotations
        assert annots['bkapp.paas.bk.tencent.com/addons'] == '["mysql"]'
        assert len(blank_resource.spec.addons) == 1


class TestEnvVarsManifestConstructor:
    def test_integrated(self, bk_module, bk_stag_env, blank_resource):
        ConfigVar.objects.create(module=bk_module, environment=bk_stag_env, key='FOO_STAG', value='1')
        ConfigVar.objects.create(module=bk_module, environment=bk_stag_env, key='BAR', value='1')
        ConfigVar.objects.create(
            module=bk_module,
            environment_id=ENVIRONMENT_ID_FOR_GLOBAL,
            key='BAR',
            value='2',
            is_global=True,
        )

        EnvVarsManifestConstructor().apply_to(blank_resource, bk_module)
        assert blank_resource.spec.configuration.env == [EnvVar(name='BAR', value='2')]
        assert blank_resource.spec.envOverlay.envVariables == [
            EnvVarOverlay(envName='stag', name='BAR', value='1'),
            EnvVarOverlay(envName='stag', name='FOO_STAG', value='1'),
        ]


class TestProcessesManifestConstructor:
    @pytest.mark.parametrize(
        "plan_name, expected",
        [
            ("", ResQuotaPlan.P_DEFAULT),
            (settings.DEFAULT_PROC_SPEC_PLAN, ResQuotaPlan.P_2C1G),
            (settings.PREMIUM_PROC_SPEC_PLAN, ResQuotaPlan.P_2C2G),
            (settings.ULTIMATE_PROC_SPEC_PLAN, ResQuotaPlan.P_4C4G),
        ],
    )
    def test_get_quota_plan(self, plan_name, expected):
        assert ProcessesManifestConstructor().get_quota_plan(plan_name) == expected

    @pytest.mark.parametrize(
        "build_method, is_cnb_runtime, expected",
        [
            (RuntimeType.BUILDPACK, False, (DEFAULT_SLUG_RUNNER_ENTRYPOINT, ["start", "web"])),
            (RuntimeType.BUILDPACK, True, (["web"], [])),
            (RuntimeType.DOCKERFILE, False, (['python'], ['-m', 'http.server'])),
        ],
    )
    def test_get_command_and_args(self, bk_module, process_web, build_method, is_cnb_runtime, expected):
        cfg = BuildConfig.objects.get_or_create_by_module(bk_module)
        cfg.build_method = build_method
        cfg.save()
        with mock.patch("paasng.platform.bkapp_model.manifest.ModuleRuntimeManager.is_cnb_runtime", is_cnb_runtime):
            assert ProcessesManifestConstructor().get_command_and_args(bk_module, process_web) == expected

    def test_integrated(self, bk_module, blank_resource, process_web):
        ProcessesManifestConstructor().apply_to(blank_resource, bk_module)
        assert LEGACY_PROC_IMAGE_ANNO_KEY not in blank_resource.metadata.annotations
        assert blank_resource.spec.dict(include={"processes"}) == {
            "processes": [
                {
                    "name": "web",
                    "replicas": 1,
                    "command": ["bash", "/runner/init"],
                    "args": ["start", "web"],
                    "targetPort": 8000,
                    "resQuotaPlan": "default",
                    "autoscaling": None,
                    "cpu": "500m",
                    "memory": "256Mi",
                    "image": None,
                    "imagePullPolicy": "IfNotPresent",
                }
            ]
        }

    @pytest.fixture
    def v1alpha1_process_web(self, bk_module, process_web) -> ModuleProcessSpec:
        process_web.image = "python:latest"
        process_web.image_credential_ame = "auto-generated"
        process_web.save(update_fields=["image", "image_credential_ame"])
        return process_web

    def test_v1alpha1(self, bk_module, blank_resource, v1alpha1_process_web):
        ProcessesManifestConstructor().apply_to(blank_resource, bk_module)
        assert (
            blank_resource.metadata.annotations[LEGACY_PROC_IMAGE_ANNO_KEY]
            == '{"web": {"image": "python:latest", "policy": "IfNotPresent"}}'
        )


def test_get_manifest(bk_module):
    manifest = get_manifest(bk_module)
    assert len(manifest) > 0
    assert manifest[0]['kind'] == 'BkApp'
