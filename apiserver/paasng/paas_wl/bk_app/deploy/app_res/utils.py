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

"""high level scheduler functions related with app"""

import logging
from typing import TYPE_CHECKING

from paas_wl.infras.resources.kube_res.base import Schedule
from paas_wl.infras.resources.utils.basic import (
    get_cluster_by_app,
    get_full_node_selector,
    get_full_tolerations,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from paas_wl.bk_app.applications.models import WlApp


def get_schedule_config(app: "WlApp") -> "Schedule":
    """Get the schedule config of an app."""
    return Schedule(
        cluster_name=get_cluster_by_app(app).name,
        node_selector=get_full_node_selector(app),
        tolerations=get_full_tolerations(app),
    )
