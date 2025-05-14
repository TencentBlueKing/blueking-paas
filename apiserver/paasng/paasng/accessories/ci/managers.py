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
from typing import TYPE_CHECKING, Dict, Type

from paasng.accessories.ci.exceptions import NotSupportedCIBackend

if TYPE_CHECKING:
    from paasng.accessories.ci.base import CIManager

logger = logging.getLogger(__name__)


_ci_managers_map: Dict[str, Type["CIManager"]] = {}


def register_ci_manager_cls(manager: Type["CIManager"]):
    _ci_managers_map[manager.backend] = manager


def get_ci_manager_cls_by_backend(backend: str):
    try:
        return _ci_managers_map[backend]
    except KeyError:
        raise NotSupportedCIBackend(backend)
