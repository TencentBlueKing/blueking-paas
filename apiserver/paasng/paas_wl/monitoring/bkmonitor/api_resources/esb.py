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
from bkapi_client_core.esb import ESBClient, Operation, OperationGroup, bind_property
from bkapi_client_core.esb import generic_type_partial as _partial
from bkapi_client_core.esb.django_helper import get_client_by_username as _get_client_by_username


class Group(OperationGroup):
    """蓝鲸监控在 ESB 上注册的 API"""

    # 统一查询时序数据
    promql_query = bind_property(
        Operation,
        name='promql_query',
        method='POST',
        path='/api/c/compapi/v2/monitor_v3/graph_promql_query/',
    )


class Client(ESBClient):
    """ESB Components"""

    monitor_v3 = bind_property(Group, name="monitor_v3")


get_client_by_username = _partial(Client, _get_client_by_username)
