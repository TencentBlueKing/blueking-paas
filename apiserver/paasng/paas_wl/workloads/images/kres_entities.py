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
from dataclasses import dataclass
from typing import Dict, List

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.infras.cluster.constants import ClusterAnnotationKey
from paas_wl.infras.cluster.utils import get_cluster_by_app, get_image_registry_by_app
from paas_wl.infras.resources.base import kres
from paas_wl.infras.resources.kube_res.base import AppEntity, AppEntityManager
from paas_wl.infras.resources.kube_res.exceptions import AppEntityNotFound
from paas_wl.utils.text import b64encode
from paas_wl.workloads.images.entities import ImageCredential
from paas_wl.workloads.images.kres_slzs import ImageCredentialsDeserializer, ImageCredentialsSerializer
from paas_wl.workloads.images.models import AppImageCredential
from paas_wl.workloads.images.utils import make_image_pull_secret_name

logger = logging.getLogger(__name__)


@dataclass
class ImageCredentials(AppEntity):
    credentials: List[ImageCredential]

    class Meta:
        kres_class = kres.KSecret
        deserializer = ImageCredentialsDeserializer
        serializer = ImageCredentialsSerializer

    @classmethod
    def load_from_app(cls, app: WlApp) -> "ImageCredentials":
        qs = AppImageCredential.objects.filter(app=app)
        credentials = [
            ImageCredential(registry=instance.registry, username=instance.username, password=instance.password)
            for instance in qs
        ]

        def should_inject_builtin_image_credential():
            # 明确说明当前集群不注入内置镜像凭证的，需要跳过（如：用户托管的集群的情况）
            annos = get_cluster_by_app(app).annotations
            return annos.get(ClusterAnnotationKey.SKIP_INJECT_BUILTIN_IMAGE_CREDENTIAL) != "true"

        if should_inject_builtin_image_credential():
            reg = get_image_registry_by_app(app)
            # 仅 host 不为空时才注入
            if reg.host:
                credentials.append(ImageCredential(registry=reg.host, username=reg.username, password=reg.password))

        return ImageCredentials(
            app=app,
            name=make_image_pull_secret_name(app),
            credentials=credentials,
        )

    def build_dockerconfig(self) -> Dict:
        """transform credentials to docker config json format"""
        return {
            "auths": {
                item.registry: {
                    "username": item.username,
                    "password": item.password,
                    "auth": b64encode(f"{item.username}:{item.password}"),
                }
                for item in self.credentials
            }
        }

    def build_app_registry_auth(self) -> Dict:
        """transform credentials to CNB required format"""
        return {item.registry: "Basic " + b64encode(f"{item.username}:{item.password}") for item in self.credentials}


class ImageCredentialsManager(AppEntityManager[ImageCredentials]):
    def __init__(self):
        super().__init__(ImageCredentials)

    def delete(self, res: ImageCredentials, non_grace_period: bool = False):
        namespace = res.app.namespace
        secret_name = res.name

        try:
            existed = self.get(app=res.app, name=secret_name)
        except AppEntityNotFound:
            logger.info("Secret<%s/%s> does not exist, will skip delete", namespace, secret_name)
            return None
        return super().delete(existed, non_grace_period)


credentials_kmodel = ImageCredentialsManager()
