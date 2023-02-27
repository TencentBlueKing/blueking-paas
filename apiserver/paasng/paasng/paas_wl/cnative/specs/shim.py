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
import json
from typing import List, Optional

from paas_wl.cnative.specs.constants import (
    BKAPP_CODE_ANNO_KEY,
    BKAPP_NAME_KEY,
    BKAPP_REGION_KEY,
    BKPAAS_ADDONS_ANNO_KEY,
    BKPAAS_DEPLOY_ID_ANNO_KEY,
    ENVIRONMENT_ANNO_KEY,
    IMAGE_CREDENTIALS_REF_ANNO_KEY,
    MODULE_NAME_ANNO_KEY,
)
from paas_wl.cnative.specs.models import AppModelDeploy
from paas_wl.cnative.specs.v1alpha1.bk_app import BkAppResource
from paas_wl.platform.applications.models import EngineApp
from paas_wl.workloads.images.models import AppImageCredential, ImageCredentialRef
from paasng.dev_resources.servicehub.manager import mixed_service_mgr
from paasng.paas_wl.cnative.specs.configurations import generate_builtin_configurations, merge_envvars
from paasng.paas_wl.networking.ingress.addrs import EnvAddresses
from paasng.platform.applications.models import ModuleEnvironment


def default_bkapp_name(env: ModuleEnvironment) -> str:
    """Get name of the default BkApp resource by env.

    :param env: ModuleEnv object
    :return: BkApp resource name
    """
    # TODO: Should we add "environment" field to name? Result may exceeds the
    # max-length limit on the operator side.
    return f'{env.application.code}'


def build_manifest(env: ModuleEnvironment, deploy: AppModelDeploy, credential_refs: List[ImageCredentialRef]):
    """inject bkpaas-specific properties to annotations

    :param env: ModuleEnv object
    :param credential_refs: Image credential ref objects
    """
    engine_app = EngineApp.objects.get(pk=env.engine_app_id)
    manifest = BkAppResource(**deploy.revision.json_value)
    manifest.metadata.annotations[BKPAAS_DEPLOY_ID_ANNO_KEY] = str(deploy.pk)
    application = env.application

    # inject bkapp basic info
    manifest.metadata.annotations.update(
        {
            BKAPP_REGION_KEY: application.region,
            BKAPP_NAME_KEY: application.name,
            BKAPP_CODE_ANNO_KEY: application.code,
            MODULE_NAME_ANNO_KEY: env.module.name,
            ENVIRONMENT_ANNO_KEY: env.environment,
        }
    )

    # inject addons services
    manifest.metadata.annotations[BKPAAS_ADDONS_ANNO_KEY] = json.dumps(
        [svc.name for svc in mixed_service_mgr.list_binded(env.module)]
    )

    # flush credentials and inject a flag to tell operator that workloads have crated the secret
    if credential_refs:
        AppImageCredential.objects.flush_from_refs(
            application=application, engine_app=engine_app, references=credential_refs
        )
        manifest.metadata.annotations[IMAGE_CREDENTIALS_REF_ANNO_KEY] = "true"
    else:
        manifest.metadata.annotations[IMAGE_CREDENTIALS_REF_ANNO_KEY] = ""

    manifest.spec.configuration.env = merge_envvars(
        manifest.spec.configuration.env, generate_builtin_configurations(env=env)
    )

    data = manifest.dict()
    # refresh status.conditions
    data["status"] = {"conditions": []}
    return data


def get_exposed_url(env: ModuleEnvironment) -> Optional[str]:
    """Get exposed URL for given env"""
    if addrs := EnvAddresses(env).get():
        return addrs[0].url
    return None
