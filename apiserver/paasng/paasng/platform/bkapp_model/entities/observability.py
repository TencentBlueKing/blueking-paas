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

from typing import Dict, List, Optional

from pydantic import BaseModel

from paasng.utils.structure import prepare_json_field


class Metric(BaseModel):
    """Metric is monitor metric config for process services

    :param process: process name
    :param service_name: name of the process service
    :param path: path of the metric api
    :param params: params of the metric api
    """

    process: str
    service_name: str
    path: str
    params: Optional[Dict[str, str]] = None


@prepare_json_field
class Monitoring(BaseModel):
    metrics: Optional[List[Metric]] = None


class Observability(BaseModel):
    monitoring: Optional[Monitoring] = None
