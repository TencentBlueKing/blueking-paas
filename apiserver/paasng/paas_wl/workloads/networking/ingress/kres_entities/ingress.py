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
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List

from django.utils.functional import lazy

from paas_wl.infras.resources.base import kres
from paas_wl.infras.resources.kube_res.base import AppEntity, AppEntityManager
from paas_wl.workloads.networking.ingress.entities import PIngressDomain
from paas_wl.workloads.networking.ingress.kres_slzs.ingress import make_deserializers, make_serializers

if TYPE_CHECKING:
    from paas_wl.bk_app.applications.models.app import WlApp

logger = logging.getLogger(__name__)


@dataclass
class ProcessIngress(AppEntity):
    """Ingress object for process, external service

    :param annotations: extra annotations
    """

    domains: List[PIngressDomain]
    service_name: str
    service_port_name: str

    server_snippet: str = ""
    configuration_snippet: str = ""

    # Whether to rewrite path to "/" when request matches path pattern, for example:
    # when path pattern is "/foo/" and user is requesting "/foo/bar", the path will be rewritten
    # to "/bar" if `rewrite_to_root`` is True.
    rewrite_to_root: bool = False

    # Whether to set http header `X-Script-Name` to all request,
    # which means the sub-path provided by platform or custom domain
    # This config should always bo True, except those ingresses managed by `LegacyAppIngressMgr`
    set_header_x_script_name: bool = True
    annotations: Dict = field(default_factory=dict)

    class Meta:
        kres_class = kres.KIngress
        serializers = lazy(make_serializers, list)()
        deserializers = lazy(make_deserializers, list)()


ingress_kmodel: AppEntityManager[ProcessIngress, "WlApp"] = AppEntityManager(ProcessIngress)
