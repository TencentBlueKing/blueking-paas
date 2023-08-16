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


class MonitorV3Group(OperationGroup):
    """蓝鲸监控在 ESB 上注册的 API

    https://github.com/Tencent/bk-PaaS/blob/ft_upgrade_py3/paas2/esb/components/confapis/monitor_v3/monitor_v3.yaml
    """

    # 快速创建APM应用
    create_apm_application = bind_property(
        Operation,
        name="create_apm_application",
        method="POST",
        path="/api/c/compapi/v2/monitor_v3/apm/create_application/",
    )
    # 创建空间
    metadata_create_space = bind_property(
        Operation,
        name="metadata_create_space",
        method="POST",
        path="/api/c/compapi/v2/monitor_v3/metadata_create_space/",
    )
    # 更新空间
    metadata_update_space = bind_property(
        Operation,
        name="metadata_update_space",
        method="POST",
        path="/api/c/compapi/v2/monitor_v3/metadata_update_space/",
    )
    # 查询空间实例详情
    metadata_get_space_detail = bind_property(
        Operation,
        name="metadata_get_space_detail",
        method="GET",
        path="/api/c/compapi/v2/monitor_v3/metadata_get_space_detail/",
    )
    # 查询告警记录
    search_alert = bind_property(
        Operation,
        name="search_alert",
        method="POST",
        path="/api/c/compapi/v2/monitor_v3/search_alert/",
    )
    # 统一查询时序数据
    promql_query = bind_property(
        Operation,
        name='promql_query',
        method='POST',
        path='/api/c/compapi/v2/monitor_v3/graph_promql_query/',
    )


class Client(ESBClient):
    """ESB Components"""

    monitor_v3 = bind_property(MonitorV3Group, name="monitor_v3")


get_client_by_username = _partial(Client, _get_client_by_username)
