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

"""
The "fieldmgr" is a module that helps to handle bkapp model updates from multiple
sources. It tries to produce the best result for the update by introducing and tracking
a "manager" for each field.
"""

from .constants import ManagerType
from .fields import (
    F_DOMAIN_RESOLUTION,
    F_SVC_DISCOVERY,
    f_overlay_autoscaling,
    f_overlay_mounts,
    f_overlay_replicas,
    f_overlay_res_quotas,
)
from .managers import FieldManager

__all__ = [
    "ManagerType",
    "F_SVC_DISCOVERY",
    "F_DOMAIN_RESOLUTION",
    "FieldManager",
    "f_overlay_autoscaling",
    "f_overlay_mounts",
    "f_overlay_replicas",
    "f_overlay_res_quotas",
]
