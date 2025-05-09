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
from contextlib import contextmanager
from typing import Dict, Iterator, List

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.cnative.specs.exceptions import InvalidImageCredentials
from paas_wl.infras.resources.base import kres
from paas_wl.workloads.configuration.secret.constants import SecretType
from paas_wl.workloads.configuration.secret.kres_entities import Secret, secret_kmodel
from paas_wl.workloads.images.entities import ImageCredentialRef
from paas_wl.workloads.images.kres_entities import ImageCredentialsManager as _ImageCredentialsManager
from paas_wl.workloads.images.models import AppUserCredential
from paasng.accessories.servicehub.services import EngineAppInstanceRel
from paasng.accessories.servicehub.tls import list_provisioned_tls_enabled_rels
from paasng.accessories.services.models import PreCreatedInstance
from paasng.accessories.services.utils import gen_addons_cert_secret_name
from paasng.platform.applications.models import Application, ModuleEnvironment

logger = logging.getLogger(__name__)


def split_image(repository: str) -> str:
    return repository.rsplit(":", 1)[0]


def validate_references(application: Application, references: List[ImageCredentialRef]):
    """validate if the reference credentials is defined

    :raises: ValueError if the reference credentials is undefined
    TODO: 验证 credential 是否可以拉取对应的镜像
    """
    request_names = {ref.credential_name for ref in references}
    all_names = set(AppUserCredential.objects.list_all_name(application))
    if missing_names := request_names - all_names:
        raise InvalidImageCredentials(f"missing credentials {missing_names}")


class ImageCredentialsManager(_ImageCredentialsManager):
    """An ImageCredentialsManager using given k8s client, the client must be closed by outer logic"""

    def __init__(self, client):
        super().__init__()
        self._client = client

    def _kres(self, app: WlApp, api_version: str = "") -> Iterator[kres.BaseKresource]:
        """return kres object using given k8s client"""
        yield self.entity_type.Meta.kres_class(self._client, api_version=api_version)

    kres = contextmanager(_kres)


def get_tls_certs_from_addons_rel(rel: EngineAppInstanceRel) -> Dict[str, str] | None:
    """获取增强服务 TLS 证书内容"""
    cfg = rel.get_instance().config

    tls = None
    # 预先创建的资源实例 -> 资源池类型，证书数据存在 PreCreatedInstance.config 中
    if cfg.get("is_pre_created"):
        if pk := cfg.get("__pk__"):
            pre_created_inst = PreCreatedInstance.objects.get(pk=pk)
            tls = pre_created_inst.config.get("tls")
    # 其他情况下，证书存在方案配置中
    else:
        tls = rel.get_plan().config.get("tls")

    if not tls:
        return None

    tls_certs = {}
    if ca := tls.get("ca"):
        tls_certs["ca.crt"] = ca

    cert, cert_key = tls.get("cert"), tls.get("key")
    if cert and cert_key:
        tls_certs.update({"tls.crt": cert, "tls.key": cert_key})

    return tls_certs


def deploy_addons_tls_certs(env: ModuleEnvironment):
    """下发增强服务 TLS 证书（如果需要的话）"""
    # 环境信息（日志打印用）
    env_info = f"App: {env.application.code}, Module: {env.module.name}, Env: {env.environment}"

    for rel in list_provisioned_tls_enabled_rels(env):
        svc_inst = rel.get_instance()
        cfg = svc_inst.config

        tls_certs = get_tls_certs_from_addons_rel(rel)
        if not tls_certs:
            logger.warning("%s, service instance %s cannot generate tls certs, skip...", env_info, svc_inst.uuid)
            continue

        secret_name = gen_addons_cert_secret_name(cfg["provider_name"])
        # Q: 为什么不使用 SecretType.TLS 类型？
        # A: 因为 TLS 类型的 Secret 会强制检查 tls.crt, tls.key 是否存在，但是我们如果只使用单向认证，
        # 则只需要也只会提供 ca.crt，此时如果使用 TLS 类型的 Secret 会出错，因此还是使用 Opaque 类型的 Secret 即可
        secret_kmodel.upsert(Secret(app=env.wl_app, name=secret_name, type=SecretType.OPAQUE, data=tls_certs))
