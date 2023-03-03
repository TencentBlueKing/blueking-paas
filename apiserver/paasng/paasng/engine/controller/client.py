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
"""Client to communicate with controller
"""
import logging
from typing import TYPE_CHECKING

from blue_krill.auth.jwt import ClientJWTAuth, JWTAuthConf

from paas_wl.cluster.utils import get_cluster_by_app
from paas_wl.networking.egress.models import RCStateAppBinding, RegionClusterState

if TYPE_CHECKING:
    from paasng.engine.models import EngineApp


logger = logging.getLogger(__name__)


class ControllerClient:
    """A Client for calling controller(workloads's system part) APIs"""

    _client_role = 'internal-sys'

    def __init__(self, controller_host: str, jwt_conf: JWTAuthConf):
        self.controller_host = controller_host
        jwt_conf.role = self._client_role
        self.auth_instance = ClientJWTAuth(jwt_conf)

    ################
    # Regular Path #
    ################

    def app_rcsbinding__create(self, engine_app: 'EngineApp'):
        wl_engine_app = engine_app.to_wl_obj()
        cluster = get_cluster_by_app(wl_engine_app)
        state = RegionClusterState.objects.filter(region=wl_engine_app.region, cluster_name=cluster.name).latest()
        RCStateAppBinding.objects.create(app=wl_engine_app, state=state)

    def app_rcsbinding__destroy(self, engine_app: 'EngineApp'):
        wl_engine_app = engine_app.to_wl_obj()
        binding = RCStateAppBinding.objects.get(app=wl_engine_app)
        # Update app scheduling config
        # TODO: Below logic is safe be removed as long as the node_selector will be fetched
        # dynamically by querying for binding state.
        latest_config = wl_engine_app.to_wl_obj().latest_config
        # Remove labels related with current binding
        for key in binding.state.to_labels():
            latest_config.node_selector.pop(key, None)
        latest_config.save()
        binding.delete()

    # Region Cluster State binding end
