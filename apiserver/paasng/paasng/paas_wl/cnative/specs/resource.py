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

from kubernetes.dynamic.exceptions import ResourceNotFoundError

from paas_wl.cnative.specs import credentials
from paas_wl.cnative.specs.constants import IMAGE_CREDENTIALS_REF_ANNO_KEY
from paas_wl.cnative.specs.v1alpha1.bk_app import BkAppResource
from paas_wl.platform.applications.models import EngineApp
from paas_wl.resources.base import crd
from paas_wl.resources.base.exceptions import ResourceMissing
from paas_wl.resources.base.kres import KNamespace
from paas_wl.resources.utils.basic import get_client_by_app
from paas_wl.workloads.images.entities import ImageCredentials
from paasng.paas_wl.cnative.specs.addresses import AddrResourceManager, save_addresses
from paasng.paas_wl.cnative.specs.shim import default_bkapp_name
from paasng.platform.applications.models import ModuleEnvironment

logger = logging.getLogger(__name__)


def get_mres_from_cluster(env: ModuleEnvironment) -> Optional[BkAppResource]:
    """Get the application's model resource in given environment, if no resource
    can be found, return `None`.
    """
    engine_app = EngineApp.objects.get_by_env(env)
    with get_client_by_app(engine_app) as client:
        # TODO: Provide apiVersion or using AppEntity(after some adapting works) to make
        # code more robust.
        try:
            data = crd.BkApp(client).get(default_bkapp_name(env), namespace=engine_app.namespace)
        except ResourceNotFoundError:
            logger.info('Resource BkApp not found in cluster')
            return None
        except ResourceMissing:
            logger.info('BkApp not found in %s, app: %s', engine_app.namespace, env.application)
            return None
    return BkAppResource(**data)


def deploy(env: ModuleEnvironment, manifest: Dict) -> Dict:
    """
    Create or update(replace) bkapp manifest in cluster

    :param env: The env to be deployed.
    :param manifest: Application manifest data.
    :raise: CreateServiceAccountTimeout 当创建 SA 超时（含无默认 token 的情况）时抛出异常
    """
    engine_app = EngineApp.objects.get(pk=env.engine_app_id)
    with get_client_by_app(engine_app) as client:
        # 若命名空间不存在，则提前创建（若为新建命名空间，需要等待 ServiceAccount 就绪）
        namespace_client = KNamespace(client)
        _, created = namespace_client.get_or_create(name=engine_app.namespace)
        if created:
            namespace_client.wait_for_default_sa(namespace=engine_app.namespace)

        if manifest["metadata"]["annotations"].get(IMAGE_CREDENTIALS_REF_ANNO_KEY) == "true":
            # 下发镜像访问凭证(secret)
            image_credentials = ImageCredentials.load_from_app(engine_app)
            credentials.ImageCredentialsManager(client).upsert(image_credentials)

        # 创建或更新 BkApp
        bkapp, _ = crd.BkApp(client).create_or_update(
            default_bkapp_name(env),
            namespace=engine_app.namespace,
            body=manifest,
            update_method='patch',
            content_type='application/merge-patch+json',
        )

    # Deploy other dependencies
    deploy_networking(env)
    return bkapp.to_dict()


def deploy_networking(env: ModuleEnvironment) -> None:
    """Deploy the networking related resources for env, such as Ingress and etc."""
    save_addresses(env)
    mapping = AddrResourceManager(env).build_mapping()
    engine_app = EngineApp.objects.get(pk=env.engine_app_id)
    with get_client_by_app(engine_app) as client:
        crd.DomainGroupMapping(client).create_or_update(
            mapping.metadata.name,
            namespace=engine_app.namespace,
            body=mapping.to_deployable(),
            update_method='patch',
            content_type='application/merge-patch+json',
        )
