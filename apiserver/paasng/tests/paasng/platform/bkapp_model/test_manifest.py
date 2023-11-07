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
import functools
from unittest import mock

import pytest
from django.conf import settings
from django_dynamic_fixture import G

from paas_wl.bk_app.cnative.specs.constants import (
    LEGACY_PROC_IMAGE_ANNO_KEY,
    ApiVersion,
    MountEnvName,
    ResQuotaPlan,
    VolumeSourceType,
)
from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppHooks, BkAppResource, BkAppSpec
from paas_wl.bk_app.cnative.specs.crd.bk_app import ConfigMapSource as ConfigMapSourceSpec
from paas_wl.bk_app.cnative.specs.crd.bk_app import EnvVar, EnvVarOverlay
from paas_wl.bk_app.cnative.specs.crd.bk_app import Mount as MountSpec
from paas_wl.bk_app.cnative.specs.crd.bk_app import MountOverlay, ObjectMetadata, VolumeSource
from paas_wl.bk_app.cnative.specs.models import Mount
from paas_wl.bk_app.processes.models import initialize_default_proc_spec_plans
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.services.models import Plan, Service, ServiceCategory
from paasng.platform.bkapp_model.manifest import (
    DEFAULT_SLUG_RUNNER_ENTRYPOINT,
    AddonsManifestConstructor,
    BuiltinAnnotsManifestConstructor,
    EnvVarsManifestConstructor,
    HooksManifestConstructor,
    MountsManifestConstructor,
    ProcessesManifestConstructor,
    apply_builtin_env_vars,
    apply_env_annots,
    get_manifest,
)
from paasng.platform.bkapp_model.models import ModuleProcessSpec, ProcessSpecEnvOverlay
from paasng.platform.engine.constants import RuntimeType
from paasng.platform.engine.models.config_var import ENVIRONMENT_ID_FOR_GLOBAL, ConfigVar
from paasng.platform.modules.constants import DeployHookType
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


@pytest.fixture
def process_web_overlay(process_web) -> ProcessSpecEnvOverlay:
    """An overlay data for web process"""
    return G(
        ProcessSpecEnvOverlay,
        proc_spec=process_web,
        environment_name='stag',
        target_replicas=10,
        plan_name='Starter',
        autoscaling=True,
        scaling_config={
            "minReplicas": 1,
            "maxReplicas": 5,
            "policy": 'default',
        },
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


class TestBuiltinAnnotsManifestConstructor:
    def test_normal(self, bk_module, blank_resource):
        app = bk_module.application
        BuiltinAnnotsManifestConstructor().apply_to(blank_resource, bk_module)

        annots = blank_resource.metadata.annotations
        assert annots['bkapp.paas.bk.tencent.com/image-credentials'] == 'true'
        assert annots['bkapp.paas.bk.tencent.com/module-name'] == bk_module.name
        assert annots['bkapp.paas.bk.tencent.com/name'] == app.name
        assert annots['bkapp.paas.bk.tencent.com/region'] == app.region
        assert annots['bkapp.paas.bk.tencent.com/use-cnb'] == 'false'


class TestProcessesManifestConstructor:
    @pytest.mark.parametrize(
        "plan_name, expected",
        [
            ("", ResQuotaPlan.P_DEFAULT),
            (settings.DEFAULT_PROC_SPEC_PLAN, ResQuotaPlan.P_2C1G),
            (settings.PREMIUM_PROC_SPEC_PLAN, ResQuotaPlan.P_2C2G),
            # Memory 稀缺性比 CPU 要高, 转换时只关注 Memory
            (settings.ULTIMATE_PROC_SPEC_PLAN, ResQuotaPlan.P_2C4G),
            (ResQuotaPlan.P_2C1G, ResQuotaPlan.P_2C1G),
        ],
    )
    def test_get_quota_plan(self, plan_name, expected):
        initialize_default_proc_spec_plans()
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

    def test_integrated(self, bk_module, blank_resource, process_web, process_web_overlay):
        initialize_default_proc_spec_plans()
        ProcessesManifestConstructor().apply_to(blank_resource, bk_module)
        assert LEGACY_PROC_IMAGE_ANNO_KEY not in blank_resource.metadata.annotations
        assert blank_resource.spec.dict(include={"processes", "envOverlay"}) == {
            "processes": [
                {
                    "name": "web",
                    "replicas": 1,
                    "command": ["bash", "/runner/init"],
                    "args": ["start", "web"],
                    "targetPort": 8000,
                    "resQuotaPlan": "default",
                    "autoscaling": None,
                    "cpu": None,
                    "memory": None,
                    "image": None,
                    "imagePullPolicy": None,
                }
            ],
            "envOverlay": {
                "replicas": [{'envName': 'stag', 'process': 'web', 'count': 10}],
                'autoscaling': [
                    {
                        "envName": "stag",
                        "process": "web",
                        "minReplicas": 1,
                        "maxReplicas": 5,
                        "policy": 'default',
                    }
                ],
                'envVariables': None,
                'mounts': None,
                'resQuotas': [
                    {
                        "envName": "stag",
                        "process": "web",
                        # The plan name should have been transformed.
                        "plan": "2C1G",
                    }
                ],
            },
        }

    @pytest.fixture
    def v1alpha1_process_web(self, bk_module, process_web) -> ModuleProcessSpec:
        process_web.image = "python:latest"
        process_web.image_credential_name = "auto-generated"
        process_web.save(update_fields=["image", "image_credential_name"])
        return process_web

    def test_v1alpha1(self, bk_module, blank_resource, v1alpha1_process_web):
        ProcessesManifestConstructor().apply_to(blank_resource, bk_module)
        assert (
            blank_resource.metadata.annotations[LEGACY_PROC_IMAGE_ANNO_KEY]
            == '{"web": {"image": "python:latest", "policy": "IfNotPresent"}}'
        )


class TestMountsManifestConstructor:
    def test_normal(self, bk_module, blank_resource):
        create_mount = functools.partial(
            Mount.objects.create,
            module_id=bk_module.id,
            name='nginx',
            source_type=VolumeSourceType.ConfigMap,
            source_config=VolumeSource(configMap=ConfigMapSourceSpec(name='nginx-configmap')),
        )
        # Create 2 mount objects
        create_mount(mount_path='/etc/conf', environment_name=MountEnvName.GLOBAL.value)
        create_mount(mount_path='/etc/conf_stag', environment_name=MountEnvName.STAG.value)

        MountsManifestConstructor().apply_to(blank_resource, bk_module)
        assert blank_resource.spec.mounts == [
            MountSpec(
                mountPath='/etc/conf',
                name='nginx',
                source=VolumeSource(configMap=ConfigMapSourceSpec(name='nginx-configmap')),
            )
        ]
        assert blank_resource.spec.envOverlay.mounts == [
            MountOverlay(
                envName='stag',
                mountPath='/etc/conf_stag',
                name='nginx',
                source=VolumeSource(configMap=ConfigMapSourceSpec(name='nginx-configmap')),
            )
        ]


class TestHooksManifestConstructor:
    def test_normal(self, bk_module, blank_resource):
        bk_module.deploy_hooks.enable_hook(type_=DeployHookType.PRE_RELEASE_HOOK, command=["python"], args=["hook.py"])
        HooksManifestConstructor().apply_to(blank_resource, bk_module)
        assert blank_resource.spec.hooks == BkAppHooks(
            preRelease={
                "command": ["python"],
                "args": ["hook.py"],
            }
        )

    def test_proc_command(self, bk_module, blank_resource):
        bk_module.deploy_hooks.enable_hook(type_=DeployHookType.PRE_RELEASE_HOOK, proc_command="python hook.py")
        HooksManifestConstructor().apply_to(blank_resource, bk_module)
        assert blank_resource.spec.hooks == BkAppHooks(
            preRelease={
                "command": ["python"],
                "args": ["hook.py"],
            }
        )

    def test_not_found(self, bk_module, blank_resource):
        HooksManifestConstructor().apply_to(blank_resource, bk_module)
        assert blank_resource.spec.hooks == BkAppHooks()

    def test_empty_command(self, bk_module, blank_resource):
        bk_module.deploy_hooks.enable_hook(type_=DeployHookType.PRE_RELEASE_HOOK, args=["hook.py"])
        HooksManifestConstructor().apply_to(blank_resource, bk_module)
        assert blank_resource.spec.hooks == BkAppHooks(preRelease={"args": ["hook.py"]})


def test_get_manifest(bk_module):
    manifest = get_manifest(bk_module)
    assert len(manifest) > 0
    assert manifest[0]['kind'] == 'BkApp'


def test_apply_env_annots(blank_resource, bk_stag_env, with_wl_apps):
    apply_env_annots(blank_resource, bk_stag_env)

    annots = blank_resource.metadata.annotations
    assert annots['bkapp.paas.bk.tencent.com/environment'] == 'stag'
    assert annots['bkapp.paas.bk.tencent.com/wl-app-name'] == bk_stag_env.wl_app.name
    assert 'bkapp.paas.bk.tencent.com/bkpaas-deploy-id' not in annots


def test_apply_env_annots_with_deploy_id(blank_resource, bk_stag_env, with_wl_apps):
    apply_env_annots(blank_resource, bk_stag_env, deploy_id='foo-id')
    assert blank_resource.metadata.annotations['bkapp.paas.bk.tencent.com/bkpaas-deploy-id'] == 'foo-id'


def test_apply_builtin_env_vars(blank_resource, bk_stag_env):
    apply_builtin_env_vars(blank_resource, bk_stag_env)
    var_names = {item.name for item in blank_resource.spec.configuration.env}
    for name in {"BKPAAS_APP_ID", "BKPAAS_APP_SECRET", "BK_LOGIN_URL"}:
        assert name in var_names
