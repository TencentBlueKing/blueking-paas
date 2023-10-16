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
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, List

from paas_wl.bk_app.cnative.specs.constants import ACCESS_CONTROL_ANNO_KEY, BKPAAS_ADDONS_ANNO_KEY, ApiVersion
from paas_wl.bk_app.cnative.specs.crd.bk_app import (
    BkAppAddon,
    BkAppResource,
    BkAppSpec,
    EnvOverlay,
    EnvVar,
    EnvVarOverlay,
    ObjectMetadata,
)
from paas_wl.bk_app.cnative.specs.models import generate_bkapp_name
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.platform.engine.constants import AppEnvName
from paasng.platform.engine.models.config_var import ENVIRONMENT_ID_FOR_GLOBAL, ConfigVar
from paasng.platform.modules.models import Module

logger = logging.getLogger(__name__)


class ManifestConstructor(ABC):
    """Construct the manifest for bk_app model, it is usually only responsible for a small part of the manifest."""

    @abstractmethod
    def apply_to(self, model_res: BkAppResource, module: Module):
        """Apply current constructor to the model resource object.

        :param model_res: The bkapp model resource object.
        :param module: The application module.
        :raise ManifestConstructorError: Unable to apply current constructor due to errors.
        """
        raise NotImplementedError()


class AddonsManifestConstructor(ManifestConstructor):
    """Construct the "addons" part."""

    def apply_to(self, model_res: BkAppResource, module: Module):
        names = [svc.name for svc in mixed_service_mgr.list_binded(module)]
        # Modify both annotations and spec
        model_res.metadata.annotations[BKPAAS_ADDONS_ANNO_KEY] = json.dumps(names)
        for name in names:
            model_res.spec.addons.append(BkAppAddon(name=name))


class AccessControlManifestConstructor(ManifestConstructor):
    """Construct the access-control part."""

    def apply_to(self, model_res: BkAppResource, module: Module):
        try:
            from paasng.security.access_control.models import ApplicationAccessControlSwitch
        except ImportError:
            # The module is not enabled in current edition
            return

        if ApplicationAccessControlSwitch.objects.is_enabled(module.application):
            model_res.metadata.annotations[ACCESS_CONTROL_ANNO_KEY] = "true"


class BuiltinAnnotsManifestConstructor(ManifestConstructor):
    """Construct the built-in annotations."""

    def apply_to(self, model_res: BkAppResource, module: Module):
        # TODO: ref to `_inject_annotations()` method
        pass


class BuildConfigManifestConstructor(ManifestConstructor):
    """Construct the build config."""

    def apply_to(self, model_res: BkAppResource, module: Module):
        # TODO
        pass


class ProcessesManifestConstructor(ManifestConstructor):
    """Construct the processes part."""

    def apply_to(self, model_res: BkAppResource, module: Module):
        # TODO
        pass


class EnvVarsManifestConstructor(ManifestConstructor):
    """Construct the env variables part."""

    def apply_to(self, model_res: BkAppResource, module: Module):
        # The global variables
        for var in ConfigVar.objects.filter(module=module, environment_id=ENVIRONMENT_ID_FOR_GLOBAL).order_by('key'):
            model_res.spec.configuration.env.append(EnvVar(name=var.key, value=var.value))

        # The environment specific variables
        overlay = model_res.spec.envOverlay
        if not overlay:
            overlay = EnvOverlay()
        for env in [AppEnvName.STAG.value, AppEnvName.PROD.value]:
            for var in ConfigVar.objects.filter(module=module, environment=module.get_envs(env)).order_by('key'):
                if overlay.envVariables is None:
                    overlay.envVariables = []
                overlay.envVariables.append(EnvVarOverlay(envName=env, name=var.key, value=var.value))

        model_res.spec.envOverlay = overlay


def get_manifest(module: Module) -> List[Dict]:
    """Get the manifest of current module, the result might contain multiple items."""
    return [
        get_bk_app_resource(module).to_deployable(),
    ]


def get_bk_app_resource(module: Module) -> BkAppResource:
    """Get the manifest of current module.

    :param module: The module object.
    :returns: The resource object.
    """
    builders: List[ManifestConstructor] = [
        BuiltinAnnotsManifestConstructor(),
        AddonsManifestConstructor(),
        AccessControlManifestConstructor(),
        ProcessesManifestConstructor(),
        BuildConfigManifestConstructor(),
        EnvVarsManifestConstructor(),
    ]
    obj = BkAppResource(
        apiVersion=ApiVersion.V1ALPHA2,
        metadata=ObjectMetadata(name=generate_bkapp_name(module)),
        spec=BkAppSpec(),
    )
    for builder in builders:
        builder.apply_to(obj, module)
    return obj
