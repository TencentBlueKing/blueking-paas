# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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
"""回收不再使用的 KMS 配置版本：ExternalSecret（目标 Secret 随之被 GC）、ClusterSecretStore 与 KMS 凭证

ServiceAccount 由同一环境的所有版本共用，不随版本回收。
"""

import logging
from collections.abc import Callable, Iterable

from paasng.infras.kms.client import KMSClient, make_kms_client
from paasng.infras.kms.manifests import CLUSTER_SECRET_STORE_KIND, EXTERNAL_SECRET_KIND, EXTERNAL_SECRETS_API_VERSION
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.engine.constants import JobStatus
from paasng.platform.engine.models import Deployment, KMSConfigVersion

from .kube import KubeResourceClient, KubeResources

logger = logging.getLogger(__name__)

# 每个环境保留最近几次成功部署使用的版本。保留上一次的版本，覆盖滚动更新期间仍在运行的旧 Pod
KEPT_SUCCESSFUL_DEPLOYMENTS = 2

# 写入 error_reason 后，复用逻辑不会再选中该版本
RECYCLING_REASON = "recycling"


def recycle_stale_kms_config_versions(deployment: Deployment, **kwargs) -> None:
    """部署成功后，回收同一环境中不再被使用的配置版本

    比本次部署更新的版本，以及仍被未结束部署引用的版本，都不会回收，避免与紧接着开始的部署冲突。
    """
    env = deployment.app_environment
    kept_ids = list(
        Deployment.objects.filter(
            app_environment=env, status=JobStatus.SUCCESSFUL.value, kms_config_version__isnull=False
        )
        .order_by("-created")
        .values_list("kms_config_version_id", flat=True)[:KEPT_SUCCESSFUL_DEPLOYMENTS]
    )
    stale = (
        KMSConfigVersion.objects.filter(env_id=env.pk, created__lt=deployment.created)
        .exclude(id__in=kept_ids)
        .exclude(deployments__status=JobStatus.PENDING.value)
    )
    recycle_kms_config_versions(stale, **kwargs)


def recycle_module_env_kms_config_versions(env: ModuleEnvironment, **kwargs) -> None:
    """模块删除时，回收环境中的全部配置版本"""
    recycle_kms_config_versions(KMSConfigVersion.objects.filter(env_id=env.pk), **kwargs)


def recycle_kms_config_versions(
    versions: Iterable[KMSConfigVersion],
    *,
    kms_factory: Callable[[str], KMSClient] = make_kms_client,
    kube_factory: Callable[[str], KubeResourceClient] = KubeResources.for_cluster,
) -> None:
    """逐个回收配置版本。单个版本失败只记录日志，记录保留，下次回收时重试"""
    versions = list(versions)
    KMSConfigVersion.objects.filter(pk__in=[v.pk for v in versions]).update(error_reason=RECYCLING_REASON)

    for version in versions:
        try:
            kube = kube_factory(version.cluster_name)
            kube.delete(
                api_version=EXTERNAL_SECRETS_API_VERSION,
                kind=EXTERNAL_SECRET_KIND,
                name=version.resource_name,
                namespace=version.namespace,
            )
            kube.delete(
                api_version=EXTERNAL_SECRETS_API_VERSION,
                kind=CLUSTER_SECRET_STORE_KIND,
                name=version.resource_name,
                namespace=None,
            )
            if version.credential_id is not None:
                kms_factory(version.tenant_id).delete_credential(version.credential_id)
        except Exception:
            logger.exception("failed to recycle KMS config version %s", version.pk)
            continue

        version.delete()
        logger.info("KMS config version recycled: %s", version)
