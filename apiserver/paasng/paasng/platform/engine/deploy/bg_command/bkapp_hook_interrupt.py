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

import logging

from paas_wl.bk_app.cnative.specs.constants import (
    BKPAAS_DEPLOY_INTERRUPTED_ANNO_KEY,
    ApiVersion,
)
from paas_wl.core.resource import generate_bkapp_name
from paas_wl.infras.resources.base import crd
from paas_wl.infras.resources.base.kres import KPod, PatchType
from paas_wl.infras.resources.utils.basic import get_client_by_app
from paasng.platform.engine.deploy.bg_command.bkapp_hook import generate_pre_release_hook_name
from paasng.platform.engine.models.deployment import Deployment

logger = logging.getLogger(__name__)


def interrupt_cnative_pre_release(deployment: Deployment) -> None:
    """中断云原生应用的 PreRelease 阶段.

    :param deployment: 待中断的 Deployment 对象 (云原生应用).
    """
    env = deployment.app_environment
    wl_app = env.wl_app
    bkapp_name = generate_bkapp_name(env)
    deploy_id = str(deployment.bkapp_release_id)

    with get_client_by_app(wl_app) as client:
        # Step 1: 写入 deploy-interrupted annotation, 通知 operator 协调中断的部署
        body = {"metadata": {"annotations": {BKPAAS_DEPLOY_INTERRUPTED_ANNO_KEY: deploy_id}}}
        try:
            crd.BkApp(client, api_version=ApiVersion.V1ALPHA2).patch(
                name=bkapp_name,
                namespace=wl_app.namespace,
                body=body,
                ptype=PatchType.MERGE,
            )
        except Exception:
            logger.exception(
                "Failed to patch BkApp deploy-interrupted annotation, bkapp=%s deploy_id=%s",
                bkapp_name,
                deploy_id,
            )

        # Step 2: best-effort 删除 PreRelease Hook Pod
        pod_name = generate_pre_release_hook_name(bkapp_name, deployment.bkapp_release_id)
        try:
            KPod(client).delete(name=pod_name, namespace=wl_app.namespace, raise_if_non_exists=True)
        except Exception:
            logger.exception("Failed to delete pre-release hook pod %s", pod_name)
