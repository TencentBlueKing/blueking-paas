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
from typing import Dict, Optional

from attrs import define
from kubernetes.dynamic.exceptions import ResourceNotFoundError

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.cnative.specs.addresses import AddrResourceManager, save_addresses
from paas_wl.bk_app.cnative.specs.constants import (
    ApiVersion,
    ConditionStatus,
    DeployStatus,
    MResConditionType,
    MResPhaseType,
)
from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppResource, MetaV1Condition
from paas_wl.bk_app.cnative.specs.credentials import ImageCredentialsManager
from paas_wl.bk_app.cnative.specs.models import generate_bkapp_name
from paas_wl.infras.resources.base import crd
from paas_wl.infras.resources.base.exceptions import ResourceMissing
from paas_wl.infras.resources.utils.basic import get_client_by_app
from paas_wl.workloads.images.kres_entities import ImageCredentials
from paasng.platform.applications.models import ModuleEnvironment

logger = logging.getLogger(__name__)


def get_mres_from_cluster(env: ModuleEnvironment) -> Optional[BkAppResource]:
    """Get the application's model resource in given environment, if no resource
    can be found, return `None`.
    """
    wl_app = env.wl_app
    with get_client_by_app(wl_app) as client:
        try:
            data = crd.BkApp(client, api_version=ApiVersion.V1ALPHA2).get(
                generate_bkapp_name(env), namespace=wl_app.namespace
            )
        except ResourceNotFoundError:
            logger.info('Resource BkApp not found in cluster')
            return None
        except ResourceMissing:
            logger.info('BkApp not found in %s, app: %s', wl_app.namespace, env.application)
            return None
    return BkAppResource(**data)


def deploy(env: ModuleEnvironment, manifest: Dict) -> Dict:
    """
    Create or update(replace) bkapp manifest in cluster

    :param env: The env to be deployed.
    :param manifest: Application manifest data.
    :raise: CreateServiceAccountTimeout 当创建 SA 超时（含无默认 token 的情况）时抛出异常
    """
    wl_app = env.wl_app
    with get_client_by_app(wl_app) as client:
        # 下发镜像访问凭证(secret)
        image_credentials = ImageCredentials.load_from_app(wl_app)
        ImageCredentialsManager(client).upsert(image_credentials, update_method='patch')

        # 创建或更新 BkApp
        bkapp, _ = crd.BkApp(client, api_version=manifest["apiVersion"]).create_or_update(
            generate_bkapp_name(env),
            namespace=wl_app.namespace,
            body=manifest,
            update_method='replace',
            auto_add_version=True,
        )

    # Deploy other dependencies
    deploy_networking(env)
    return bkapp.to_dict()


def deploy_networking(env: ModuleEnvironment) -> None:
    """Deploy the networking related resources for env, such as Ingress etc."""
    save_addresses(env)
    mapping = AddrResourceManager(env).build_mapping()
    wl_app = WlApp.objects.get(pk=env.engine_app_id)
    with get_client_by_app(wl_app) as client:
        crd.DomainGroupMapping(client, api_version=ApiVersion.V1ALPHA1).create_or_update(
            mapping.metadata.name,
            namespace=wl_app.namespace,
            body=mapping.to_deployable(),
            update_method='patch',
            content_type='application/merge-patch+json',
        )


def delete_bkapp(env: ModuleEnvironment):
    """Delete bkapp in cluster

    :param env
    """

    wl_app = env.wl_app
    with get_client_by_app(wl_app) as client:
        crd.BkApp(client).delete(generate_bkapp_name(env), namespace=wl_app.namespace)


def delete_networking(env: ModuleEnvironment):
    """Delete network group mapping in cluster"""
    mapping = AddrResourceManager(env).build_mapping()
    wl_app = env.wl_app
    with get_client_by_app(wl_app) as client:
        crd.DomainGroupMapping(client).delete(mapping.metadata.name, namespace=wl_app.namespace)


@define
class ModelResState:
    """State of deployed app model resource

    :param status: "ready", "pending" etc.
    :param reason: Reason for current status
    :param message: Detailed message
    """

    status: DeployStatus
    reason: str
    message: str


class MresConditionParser:
    """Parse "conditions" in BkApp resource's status field"""

    def __init__(self, mres: BkAppResource):
        self.mres = mres

    def detect_state(self) -> ModelResState:
        """Detect the final state from status.conditions"""
        if self.mres.metadata.generation > self.mres.status.observedGeneration:
            return ModelResState(DeployStatus.PENDING, "Pending", "waiting for the controller to process this BkApp")

        if not self.mres.status.conditions:
            return ModelResState(DeployStatus.PENDING, "Pending", "state not initialized")

        available = self._find_condition(MResConditionType.APP_AVAILABLE)
        if available and available.status == ConditionStatus.TRUE:
            return ModelResState(DeployStatus.READY, available.reason, available.message)

        if self.mres.status.phase == MResPhaseType.AppFailed:
            for cond in self.mres.status.conditions:
                if cond.status == ConditionStatus.FALSE and cond.message:
                    return ModelResState(DeployStatus.ERROR, cond.reason, cond.message)
            return ModelResState(DeployStatus.ERROR, "Unknown", "")

        return ModelResState(DeployStatus.PROGRESSING, "Progressing", "progressing")

    def _find_condition(self, type_: MResConditionType) -> Optional[MetaV1Condition]:
        for condition in self.mres.status.conditions:
            if condition.type == type_:
                return condition
        return None
