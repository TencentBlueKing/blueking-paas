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
from typing import TYPE_CHECKING

from paas_wl.infras.resources.base.kres import KPersistentVolumeClaim
from paas_wl.infras.resources.kube_res.base import AppEntity, AppEntityManager
from paas_wl.infras.resources.kube_res.exceptions import AppEntityNotFound

from .kres_slzs import PersistentVolumeClaimDeserializer, PersistentVolumeClaimSerializer

if TYPE_CHECKING:
    from paas_wl.bk_app.applications.models import WlApp  # noqa: F401

logger = logging.getLogger(__name__)


@dataclass
class PersistentVolumeClaim(AppEntity):
    storage: str
    storage_class_name: str

    class Meta:
        kres_class = KPersistentVolumeClaim
        deserializer = PersistentVolumeClaimDeserializer
        serializer = PersistentVolumeClaimSerializer


class PersistentVolumeClaimManager(AppEntityManager[PersistentVolumeClaim, "WlApp"]):
    def __init__(self):
        super().__init__(PersistentVolumeClaim)

    def delete(self, res: PersistentVolumeClaim, non_grace_period: bool = False):
        namespace = res.app.namespace
        pvc_name = res.name

        try:
            existed_one = self.get(app=res.app, name=pvc_name)
        except AppEntityNotFound:
            logger.info("PersistentVolumeClaim<%s/%s> does not exist, will skip delete", namespace, pvc_name)
            return None
        return super().delete(existed_one, non_grace_period)

    def upsert(self, res: PersistentVolumeClaim, update_method="replace"):
        try:
            self.get(app=res.app, name=res.name)
        except AppEntityNotFound:
            # PersistentVolumeClaim 不存在时执行创建
            return super().upsert(res, update_method)
        return None


pvc_kmodel = PersistentVolumeClaimManager()
